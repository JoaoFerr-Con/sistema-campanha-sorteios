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
