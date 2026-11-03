"""Phase 2: Management of Boxes, Permissionários, Occupancies, and Staging Review."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.entities import Box, Permissionario, BoxOccupancy, ImportStagingRow, Activity
from app.core.exceptions import DomainRuleException
from app.services.audit_service import log_audit

TOTAL_MAP_BOXES = 368

def parse_excel_rows(file_path: Path) -> List[Dict[str, Any]]:
    """Parse Excel spreadsheet (.xlsx) using native zipfile and xml parsing."""
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {file_path}")

    with zipfile.ZipFile(file_path, "r") as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            st = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in st.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                texts = [t.text for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text]
                shared.append("".join(texts))

        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        extracted_rows = []

        for r in sheet.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            row_num = int(r.attrib.get("r", 0))
            cells = {}
            for c in r.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                ref = c.attrib.get("r", "")
                col = "".join(ch for ch in ref if ch.isalpha())
                t = c.attrib.get("t")
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                val = ""
                if v is not None and v.text is not None:
                    val = shared[int(v.text)] if t == "s" else v.text
                cells[col] = val.strip()

            if row_num > 8 and any(cells.values()):
                box_val = cells.get("A", "").strip()
                name_val = cells.get("B", "").strip()
                activity_val = cells.get("C", "").strip()
                extracted_rows.append({
                    "row_number": row_num,
                    "box_number": box_val,
                    "permissionario_name": name_val,
                    "activity": activity_val,
                })

        return extracted_rows

def _clean_name(name: Optional[str]) -> str:
    """Remove espaços e o ponto final usado na planilha oficial ('Fulano de Tal.')."""
    return (name or "").strip().rstrip(".").strip()


def import_spreadsheet_to_staging(db: Session, file_path: Path, user_id: Optional[int] = None,
                                  username: Optional[str] = None) -> Dict[str, Any]:
    """Carrega a planilha na área de conferência e marca divergências. Não reimporta por cima."""
    if db.query(ImportStagingRow).count() > 0:
        raise DomainRuleException(
            "A planilha já foi carregada na área de conferência. Revise as linhas existentes; "
            "uma nova carga duplicaria o histórico de decisões.", status_code=409)

    rows = parse_excel_rows(file_path)
    box_counts = Counter(r["box_number"] for r in rows if r["box_number"])
    inserted_count = anomalies_detected = 0

    for r in rows:
        flags = []
        box_num, name, activity = r["box_number"], r["permissionario_name"], r["activity"]
        if box_counts.get(box_num, 0) > 1:
            flags.append("DUP_BOX_SPREADSHEET")
        if not name:
            flags.append("EMPTY_NAME")
        elif any(token in name.upper() for token in ["VAGO", "SEM USO", "VAZIO"]):
            flags.append("MARKED_VAGO")
        if not activity:
            flags.append("EMPTY_ACTIVITY")
        if box_num and box_num.isdigit() and not (1 <= int(box_num) <= TOTAL_MAP_BOXES):
            flags.append("BOX_OUT_OF_MAP")
        if flags:
            anomalies_detected += 1
        db.add(ImportStagingRow(
            row_number=r["row_number"], raw_box_number=box_num, raw_permissionario_name=name,
            raw_activity=activity, status="PENDENTE_REVISAO", discrepancy_flags=json.dumps(flags),
        ))
        inserted_count += 1

    log_audit(db=db, action="EXCEL_IMPORT_STAGING", entity_name="ImportStagingRow", user_id=user_id,
              username=username or "SISTEMA",
              after_state={"inserted_count": inserted_count, "anomalies_detected": anomalies_detected})
    db.commit()
    return {"status": "success", "total_rows_imported": inserted_count, "anomalies_detected": anomalies_detected}


def review_staging_row(
    db: Session,
    staging_id: int,
    decision: str,
    justification: str,
    user_id: int,
    username: str,
    confirmed_box_number: Optional[str] = None,
    confirmed_permissionario_name: Optional[str] = None,
    confirmed_activity: Optional[str] = None,
    is_vago: bool = False,
) -> ImportStagingRow:
    """Decisão do administrador sobre uma linha da planilha, com justificativa registrada."""
    staging = db.query(ImportStagingRow).filter(ImportStagingRow.id == staging_id).first()
    if not staging:
        raise DomainRuleException("Linha da conferência não encontrada.", status_code=404)
    if staging.status != "PENDENTE_REVISAO":
        raise DomainRuleException(f"A linha {staging.row_number} já foi revisada ({staging.status}).", status_code=409)

    before_state = {"status": staging.status, "admin_decision": staging.admin_decision}
    final_box_number = (confirmed_box_number or staging.raw_box_number or "").strip()
    final_name = _clean_name(confirmed_permissionario_name or staging.raw_permissionario_name)
    final_activity = (confirmed_activity or staging.raw_activity or "DIVERSOS").strip().upper()
    if final_name.upper() in {"VAGO", "SEM USO", "VAZIO"}:
        is_vago = True  # a própria planilha declara o box vago

    if decision == "APROVADO":
        if not final_box_number:
            raise DomainRuleException("Informe o número do box para aprovar.")
        if not final_box_number.isdigit() or not (1 <= int(final_box_number) <= TOTAL_MAP_BOXES):
            raise DomainRuleException(f"O box precisa estar entre 1 e {TOTAL_MAP_BOXES} (mapa oficial).")
        if not is_vago and not final_name:
            raise DomainRuleException("Linha sem nome: informe o permissionário ou marque o box como vago.")

        box = db.query(Box).filter(Box.box_number == final_box_number).first()
        if not box:
            box = Box(box_number=final_box_number,
                      notes=f"Criado a partir da linha {staging.row_number} da planilha oficial.")
            db.add(box)
            db.flush()
        box.official_status = "VAGO_CONFIRMADO" if is_vago else "CONFIRMADO"

        if not db.query(Activity).filter(Activity.name == final_activity).first():
            db.add(Activity(name=final_activity))
            db.flush()

        # Encerra vínculos vigentes do box (histórico preservado)
        for occ in db.query(BoxOccupancy).filter(BoxOccupancy.box_id == box.id, BoxOccupancy.is_current == True).all():
            occ.is_current = False
            occ.end_date = datetime.utcnow()

        if not is_vago:
            perm = db.query(Permissionario).filter(Permissionario.name == final_name).first()
            if not perm:
                perm = Permissionario(name=final_name, status="ATIVO")
                db.add(perm)
                db.flush()
            db.add(BoxOccupancy(box_id=box.id, permissionario_id=perm.id, activity_name=final_activity,
                                is_current=True, authorization_term_ref=f"IMPORT-ROW-{staging.row_number}"))

    staging.status = decision
    staging.admin_decision = decision
    staging.admin_justification = justification
    staging.reviewed_by_user_id = user_id
    staging.reviewed_at = datetime.utcnow()

    log_audit(db=db, action="STAGING_REVIEW", entity_name="ImportStagingRow", entity_id=staging.id,
              user_id=user_id, username=username, before_state=before_state,
              after_state={"decision": decision, "justification": justification, "box": final_box_number,
                           "permissionario": None if is_vago else final_name, "vago": is_vago})
    db.commit()
    db.refresh(staging)
    return staging


def get_boxes_summary(db: Session) -> Dict[str, Any]:
    counts = dict(db.query(Box.official_status, func.count(Box.id)).group_by(Box.official_status).all())
    staging_pending = db.query(ImportStagingRow).filter(ImportStagingRow.status == "PENDENTE_REVISAO").count()
    staging_approved = db.query(ImportStagingRow).filter(ImportStagingRow.status == "APROVADO").count()
    total = sum(counts.values())
    return {
        "total_map_capacity": TOTAL_MAP_BOXES,
        "total_boxes_cataloged": total,
        "confirmed_active": counts.get("CONFIRMADO", 0),
        "confirmed_vacant": counts.get("VAGO_CONFIRMADO", 0),
        "under_regularization": counts.get("EM_REGULARIZACAO", 0),
        "out_of_use": counts.get("SEM_USO", 0),
        "staging_pending_review": staging_pending,
        "staging_approved": staging_approved,
    }


def get_box_map(db: Session) -> List[Dict[str, Any]]:
    """Situação de cada um dos 368 boxes do mapa, unindo o cadastro oficial e a conferência."""
    boxes = {b.box_number: b for b in db.query(Box).all()}
    staging_by_box: Dict[str, List[ImportStagingRow]] = {}
    for r in db.query(ImportStagingRow).order_by(ImportStagingRow.row_number).all():
        staging_by_box.setdefault((r.raw_box_number or "").strip(), []).append(r)

    out = []
    for n in range(1, TOTAL_MAP_BOXES + 1):
        key = str(n)
        b = boxes.get(key)
        rows = staging_by_box.get(key, [])
        pending = [r for r in rows if r.status == "PENDENTE_REVISAO"]
        flags = sorted({f for r in rows for f in json.loads(r.discrepancy_flags or "[]")})
        item = {"box_number": key, "status": "SEM_REGISTRO", "permissionario": None,
                "permissionario_id": None, "activity": None, "box_id": None,
                "pending_rows": len(pending), "flags": flags}
        if b:
            occ = next((o for o in b.occupancies if o.is_current), None)
            item.update({"status": b.official_status, "box_id": b.id,
                         "permissionario": occ.permissionario.name if occ else None,
                         "permissionario_id": occ.permissionario_id if occ else None,
                         "activity": occ.activity_name if occ else None,
                         "permissionario_status": occ.permissionario.status if occ else None})
            if pending:
                item["status_note"] = "Possui linha da planilha ainda não revisada"
        elif pending:
            item.update({"status": "PENDENTE_CONFERENCIA",
                         "permissionario": _clean_name(pending[0].raw_permissionario_name) or None,
                         "activity": pending[0].raw_activity or None})
        out.append(item)
    return out


def update_permissionario(db: Session, perm_id: int, data: Dict[str, Any], user_id: int, username: str) -> Permissionario:
    perm = db.query(Permissionario).filter(Permissionario.id == perm_id).first()
    if not perm:
        raise DomainRuleException("Permissionário não encontrado.", status_code=404)
    before = {"status": perm.status, "phone": perm.phone, "email": perm.email,
              "document": perm.document_cpf_cnpj, "sebrae": perm.sebrae_qualification_level}
    for field, attr in [("phone", "phone"), ("email", "email"), ("document_cpf_cnpj", "document_cpf_cnpj"),
                        ("status", "status"), ("sebrae_qualification_level", "sebrae_qualification_level")]:
        if data.get(field) is not None:
            setattr(perm, attr, data[field].strip() if isinstance(data[field], str) else data[field])
    log_audit(db, "PERMISSIONARIO_UPDATED", "Permissionario", entity_id=perm.id, user_id=user_id,
              username=username, before_state=before,
              after_state={**{k: data.get(k) for k in data if data.get(k) is not None},
                           "justification": data.get("justification")})
    db.commit()
    db.refresh(perm)
    return perm


# ---------------------------------------------------------------- gestão manual de permissionários e boxes

BOX_STATUSES = {"CONFIRMADO", "VAGO_CONFIRMADO", "EM_REGULARIZACAO", "SEM_USO"}


def _validate_box_number(box_number: str) -> str:
    n = (box_number or "").strip()
    if not n.isdigit() or not (1 <= int(n) <= TOTAL_MAP_BOXES):
        raise DomainRuleException(f"O box precisa ser um número entre 1 e {TOTAL_MAP_BOXES} (mapa oficial).")
    return str(int(n))


def _get_or_create_box(db: Session, box_number: str) -> Box:
    n = _validate_box_number(box_number)
    box = db.query(Box).filter(Box.box_number == n).first()
    if not box:
        box = Box(box_number=n, official_status="EM_REGULARIZACAO", notes="Criado por cadastro manual.")
        db.add(box)
        db.flush()
    return box


def _ensure_activity(db: Session, name: str) -> str:
    act = (name or "").strip().upper()
    if not act:
        raise DomainRuleException("Informe a atividade comercial do box.")
    if not db.query(Activity).filter(Activity.name == act).first():
        db.add(Activity(name=act))
        db.flush()
    return act


def _current_occupancy(db: Session, box_id: int) -> Optional[BoxOccupancy]:
    return db.query(BoxOccupancy).filter(BoxOccupancy.box_id == box_id, BoxOccupancy.is_current == True).first()


def _outstanding_vouchers(db: Session, box_id: int, permissionario_id: int) -> int:
    """Comprovantes do titular atual ainda não utilizados em campanhas aprovadas ou ativas."""
    from app.models.entities import Voucher, Campaign
    return (db.query(Voucher).join(Campaign, Campaign.id == Voucher.campaign_id)
            .filter(Voucher.box_id == box_id, Voucher.permissionario_id == permissionario_id,
                    Voucher.status.in_(["DISTRIBUIDO", "EMITIDO"]), Campaign.status.in_(["APROVADA", "ATIVA"]))
            .count())


def list_activities(db: Session) -> List[str]:
    names = {a.name for a in db.query(Activity).all()}
    names |= {o.activity_name for o in db.query(BoxOccupancy.activity_name).distinct().all() if o.activity_name}
    return sorted(names)


def create_permissionario(db: Session, data: Dict[str, Any], user_id: int, username: str) -> Permissionario:
    name = _clean_name(data.get("name"))
    if len(name) < 3:
        raise DomainRuleException("Informe o nome completo do permissionário.")
    doc = "".join(ch for ch in (data.get("document_cpf_cnpj") or "") if ch.isdigit()) or None
    if doc and len(doc) not in (11, 14):
        raise DomainRuleException("O CPF deve ter 11 dígitos ou o CNPJ 14 dígitos.")
    if db.query(Permissionario).filter(func.lower(Permissionario.name) == name.lower()).first():
        raise DomainRuleException(f"Já existe um permissionário chamado '{name}'. Abra o cadastro existente.", status_code=409)
    if doc and db.query(Permissionario).filter(Permissionario.document_cpf_cnpj == doc).first():
        raise DomainRuleException("Já existe um permissionário com este CPF/CNPJ.", status_code=409)
    perm = Permissionario(name=name, document_cpf_cnpj=doc, phone=(data.get("phone") or "").strip() or None,
                          email=(data.get("email") or "").strip().lower() or None,
                          status=data.get("status") or "ATIVO",
                          sebrae_qualification_level=data.get("sebrae_qualification_level") or "NIVEL_1_REGULAR")
    db.add(perm)
    db.flush()
    log_audit(db, "PERMISSIONARIO_CREATED", "Permissionario", entity_id=perm.id, user_id=user_id, username=username,
              after_state={"name": name, "document": doc, "status": perm.status, "origin": "cadastro manual",
                           "justification": data.get("justification")})
    if data.get("box_number"):
        assign_box(db, data["box_number"], perm.id, data.get("activity_name"), data.get("authorization_term_ref"),
                   data.get("justification") or "Cadastro de novo permissionário", user_id, username,
                   acknowledge_outstanding=bool(data.get("acknowledge_outstanding")), commit=False)
    db.commit()
    db.refresh(perm)
    return perm


def assign_box(db: Session, box_number: str, permissionario_id: int, activity_name: Optional[str],
               authorization_term_ref: Optional[str], justification: str, user_id: int, username: str,
               acknowledge_outstanding: bool = False, commit: bool = True) -> BoxOccupancy:
    """Vincula um permissionário ao box. Se houver titular, encerra o vínculo anterior (troca de titular)."""
    if not justification or len(justification.strip()) < 5:
        raise DomainRuleException("Informe a justificativa (ex.: número do termo de permissão ou processo).")
    perm = db.query(Permissionario).filter(Permissionario.id == permissionario_id).first()
    if not perm:
        raise DomainRuleException("Permissionário não encontrado.", status_code=404)
    box = _get_or_create_box(db, box_number)
    if box.official_status == "SEM_USO":
        raise DomainRuleException("Este box está marcado como sem uso. Altere a situação do box antes de vinculá-lo.")
    current = _current_occupancy(db, box.id)
    if current and current.permissionario_id == permissionario_id:
        raise DomainRuleException(f"{perm.name} já é o titular do Box {box.box_number}.")
    activity = _ensure_activity(db, activity_name or (current.activity_name if current else ""))

    previous = None
    if current:
        pending = _outstanding_vouchers(db, box.id, current.permissionario_id)
        if pending and not acknowledge_outstanding:
            raise DomainRuleException(
                f"O titular atual ({current.permissionario.name}) ainda tem {pending} comprovante(s) não utilizado(s) "
                "em campanhas em andamento. Eles continuam válidos em nome dele. Confirme a troca para prosseguir, "
                "ou cancele o lote antes.", status_code=409)
        previous = {"permissionario": current.permissionario.name, "activity": current.activity_name,
                    "since": current.start_date.isoformat(), "pending_vouchers": pending}
        current.is_current = False
        current.end_date = datetime.utcnow()

    occ = BoxOccupancy(box_id=box.id, permissionario_id=perm.id, activity_name=activity, is_current=True,
                       authorization_term_ref=(authorization_term_ref or "").strip() or None)
    db.add(occ)
    before_status = box.official_status
    box.official_status = "CONFIRMADO" if perm.status == "ATIVO" else "EM_REGULARIZACAO"
    log_audit(db, "BOX_HOLDER_TRANSFERRED" if previous else "BOX_HOLDER_ASSIGNED", "Box", entity_id=box.box_number,
              user_id=user_id, username=username,
              before_state={"status": before_status, "holder": previous},
              after_state={"status": box.official_status, "holder": perm.name, "activity": activity,
                           "term": occ.authorization_term_ref, "justification": justification})
    if commit:
        db.commit()
        db.refresh(occ)
    else:
        db.flush()
    return occ


def release_box(db: Session, box_number: str, target_status: str, justification: str, user_id: int, username: str,
                acknowledge_outstanding: bool = False) -> Box:
    """Encerra o vínculo vigente (o histórico é preservado) e marca o box como vago ou sem uso."""
    if target_status not in ("VAGO_CONFIRMADO", "SEM_USO", "EM_REGULARIZACAO"):
        raise DomainRuleException("Situação inválida para um box sem titular.")
    if not justification or len(justification.strip()) < 5:
        raise DomainRuleException("Informe a justificativa.")
    n = _validate_box_number(box_number)
    box = db.query(Box).filter(Box.box_number == n).first()
    if not box:
        raise DomainRuleException("Box sem cadastro oficial.", status_code=404)
    current = _current_occupancy(db, box.id)
    if not current:
        raise DomainRuleException("Este box não tem titular vigente.")
    pending = _outstanding_vouchers(db, box.id, current.permissionario_id)
    if pending and not acknowledge_outstanding:
        raise DomainRuleException(
            f"{current.permissionario.name} ainda tem {pending} comprovante(s) não utilizado(s) em campanhas em andamento. "
            "Confirme para encerrar o vínculo mesmo assim, ou cancele o lote antes.", status_code=409)
    current.is_current = False
    current.end_date = datetime.utcnow()
    before = box.official_status
    box.official_status = target_status
    log_audit(db, "BOX_HOLDER_RELEASED", "Box", entity_id=box.box_number, user_id=user_id, username=username,
              before_state={"status": before, "holder": current.permissionario.name, "activity": current.activity_name},
              after_state={"status": target_status, "holder": None, "pending_vouchers": pending,
                           "justification": justification})
    db.commit()
    db.refresh(box)
    return box


def update_box(db: Session, box_number: str, data: Dict[str, Any], user_id: int, username: str) -> Box:
    """Altera a situação, a atividade do titular vigente, o setor ou as observações do box."""
    if not data.get("justification") or len(data["justification"].strip()) < 5:
        raise DomainRuleException("Informe a justificativa.")
    box = _get_or_create_box(db, box_number)
    current = _current_occupancy(db, box.id)
    before = {"status": box.official_status, "sector": box.sector, "notes": box.notes,
              "activity": current.activity_name if current else None}
    status = data.get("official_status")
    if status:
        if status not in BOX_STATUSES:
            raise DomainRuleException("Situação de box inválida.")
        if status == "CONFIRMADO" and not current:
            raise DomainRuleException("Para confirmar o box, vincule um permissionário titular.")
        if status in ("VAGO_CONFIRMADO", "SEM_USO") and current:
            raise DomainRuleException("O box tem titular vigente. Use 'Encerrar vínculo' para deixá-lo vago.")
        if status == "CONFIRMADO" and current and current.permissionario.status != "ATIVO":
            raise DomainRuleException(f"O titular está com cadastro {current.permissionario.status}. "
                                      "Regularize o permissionário antes de confirmar o box.")
        box.official_status = status
    if data.get("activity_name"):
        if not current:
            raise DomainRuleException("A atividade pertence ao vínculo com o titular; este box não tem titular.")
        current.activity_name = _ensure_activity(db, data["activity_name"])
    if data.get("sector") is not None:
        box.sector = data["sector"].strip() or None
    if data.get("notes") is not None:
        box.notes = data["notes"].strip() or None
    after = {"status": box.official_status, "sector": box.sector, "notes": box.notes,
             "activity": current.activity_name if current else None, "justification": data["justification"]}
    log_audit(db, "BOX_UPDATED", "Box", entity_id=box.box_number, user_id=user_id, username=username,
              before_state=before, after_state=after)
    db.commit()
    db.refresh(box)
    return box


def box_detail(db: Session, box_number: str) -> Dict[str, Any]:
    from app.models.entities import AuditLog
    n = _validate_box_number(box_number)
    box = db.query(Box).filter(Box.box_number == n).first()
    staging = db.query(ImportStagingRow).filter(ImportStagingRow.raw_box_number == n).order_by(ImportStagingRow.row_number).all()
    logs = db.query(AuditLog).filter(AuditLog.entity_name == "Box", AuditLog.entity_id == n).order_by(AuditLog.id.desc()).all()
    occs = sorted(box.occupancies, key=lambda o: o.start_date, reverse=True) if box else []
    current = next((o for o in occs if o.is_current), None)
    return {
        "box_number": n,
        "registered": bool(box),
        "status": box.official_status if box else ("PENDENTE_CONFERENCIA" if any(r.status == "PENDENTE_REVISAO" for r in staging) else "SEM_REGISTRO"),
        "sector": box.sector if box else None,
        "notes": box.notes if box else None,
        "current": {"permissionario_id": current.permissionario_id, "permissionario": current.permissionario.name,
                    "permissionario_status": current.permissionario.status, "activity": current.activity_name,
                    "since": current.start_date.isoformat(), "term": current.authorization_term_ref,
                    "pending_vouchers": _outstanding_vouchers(db, box.id, current.permissionario_id)} if current else None,
        "holders": [{"permissionario_id": o.permissionario_id, "permissionario": o.permissionario.name, "activity": o.activity_name,
                     "start_date": o.start_date.isoformat(), "end_date": o.end_date.isoformat() if o.end_date else None,
                     "is_current": o.is_current, "term": o.authorization_term_ref} for o in occs],
        "staging_rows": [{"id": r.id, "row_number": r.row_number, "name": r.raw_permissionario_name, "activity": r.raw_activity,
                          "status": r.status, "flags": json.loads(r.discrepancy_flags or "[]")} for r in staging],
        "history": [{"timestamp": l.created_at.isoformat(), "username": l.username or "SISTEMA", "action": l.action,
                     "before": l.before_state_json, "after": l.after_state_json} for l in logs],
    }
