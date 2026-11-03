"""Talões (lotes), comprovantes, rastreabilidade e prestação de contas."""
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.core.config import settings
from app.models.entities import (
    VoucherBatch, Voucher, Box, Permissionario, Campaign, BoxOccupancy, AuditLog, Participation,
)
from app.core.exceptions import DomainRuleException, BoxNotConfirmedException
from app.services.audit_service import log_audit, mask_cpf

PREFIX_RE = re.compile(r"^[A-Z0-9]{2,10}$")
VOUCHER_STATUS_LABELS = {
    "DISTRIBUIDO": "Distribuído ao box",
    "EMITIDO": "Emitido ao consumidor",
    "UTILIZADO": "Utilizado (virou participação)",
    "CANCELADO": "Cancelado",
    "DEVOLVIDO": "Devolvido",
    "EXTRAVIADO": "Extraviado",
}
INCIDENT_STATUSES = ["EXTRAVIADO", "DEVOLVIDO", "CANCELADO"]


def create_voucher_batch(db: Session, campaign_id: int, box_id: int, permissionario_id: int, code_prefix: str,
                         start_number: int, end_number: int, user_id: int, username: str,
                         notes: Optional[str] = None) -> VoucherBatch:
    if start_number > end_number:
        raise DomainRuleException("O número inicial do talão deve ser menor ou igual ao número final.")
    total_count = end_number - start_number + 1
    if total_count > settings.max_vouchers_per_batch:
        raise DomainRuleException(f"Cada lote pode ter no máximo {settings.max_vouchers_per_batch} comprovantes.")
    if end_number > 99999:
        raise DomainRuleException("A numeração dos comprovantes vai até 99999.")

    norm_prefix = code_prefix.strip().upper()
    if not PREFIX_RE.match(norm_prefix):
        raise DomainRuleException("O prefixo deve ter de 2 a 10 letras ou números, sem espaços ou símbolos.")

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign or campaign.status not in ["APROVADA", "ATIVA"]:
        raise DomainRuleException("A campanha precisa estar Aprovada ou Ativa para receber lotes.")

    box = db.query(Box).filter(Box.id == box_id).first()
    if not box or box.official_status != "CONFIRMADO":
        raise BoxNotConfirmedException(box.box_number if box else str(box_id))

    perm = db.query(Permissionario).filter(Permissionario.id == permissionario_id).first()
    if not perm or perm.status != "ATIVO":
        raise DomainRuleException("Permissionário inexistente ou com cadastro que não está ATIVO.")

    if not db.query(BoxOccupancy).filter(BoxOccupancy.box_id == box_id, BoxOccupancy.permissionario_id == permissionario_id,
                                         BoxOccupancy.is_current == True).first():
        raise DomainRuleException(f"O permissionário '{perm.name}' não possui vínculo ativo no Box '{box.box_number}'.")

    # O código completo (PREFIXO-NNNNN) é único no sistema inteiro: a checagem de sobreposição
    # vale para qualquer campanha que use o mesmo prefixo, inclusive lotes cancelados (os códigos existem).
    overlap = db.query(VoucherBatch).filter(
        VoucherBatch.code_prefix == norm_prefix,
        and_(VoucherBatch.start_number <= end_number, VoucherBatch.end_number >= start_number),
    ).first()
    if overlap:
        where = "nesta campanha" if overlap.campaign_id == campaign_id else "em outra campanha"
        raise DomainRuleException(
            f"Conflito de intervalo: o lote #{overlap.batch_number} já utiliza "
            f"{norm_prefix}-{overlap.start_number:05d} a {norm_prefix}-{overlap.end_number:05d} {where}.")

    latest = db.query(func.max(VoucherBatch.batch_number)).filter(VoucherBatch.campaign_id == campaign_id).scalar()
    batch = VoucherBatch(campaign_id=campaign_id, permissionario_id=permissionario_id, box_id=box_id,
                         batch_number=(latest or 0) + 1, code_prefix=norm_prefix, start_number=start_number,
                         end_number=end_number, total_vouchers=total_count, distributed_by_user_id=user_id,
                         status="ATIVO", notes=notes)
    db.add(batch)
    db.flush()
    db.bulk_save_objects([
        Voucher(batch_id=batch.id, campaign_id=campaign_id, box_id=box_id, permissionario_id=permissionario_id,
                full_code=f"{norm_prefix}-{seq:05d}", sequence_number=seq, status="DISTRIBUIDO")
        for seq in range(start_number, end_number + 1)
    ])
    log_audit(db, "BATCH_CREATED", "VoucherBatch", entity_id=batch.id, user_id=user_id, username=username,
              campaign_id=campaign_id,
              after_state={"batch_number": batch.batch_number, "prefix": norm_prefix,
                           "range": f"{start_number}..{end_number}", "total": total_count,
                           "box": box.box_number, "permissionario": perm.name})
    db.commit()
    db.refresh(batch)
    return batch


def cancel_batch(db: Session, batch_id: int, reason: str, user_id: int, username: str) -> Dict[str, Any]:
    """Cancela um lote: comprovantes ainda não utilizados passam a CANCELADO; utilizados são preservados."""
    batch = db.query(VoucherBatch).filter(VoucherBatch.id == batch_id).first()
    if not batch:
        raise DomainRuleException("Lote não encontrado.", status_code=404)
    if batch.status == "CANCELADO":
        raise DomainRuleException("Este lote já está cancelado.")
    affected = db.query(Voucher).filter(Voucher.batch_id == batch.id, Voucher.status.in_(["DISTRIBUIDO", "EMITIDO"])) \
        .update({"status": "CANCELADO", "updated_at": datetime.utcnow()}, synchronize_session=False)
    batch.status = "CANCELADO"
    batch.cancel_reason = reason
    log_audit(db, "BATCH_CANCELLED", "VoucherBatch", entity_id=batch.id, user_id=user_id, username=username,
              campaign_id=batch.campaign_id, before_state={"status": "ATIVO"},
              after_state={"status": "CANCELADO", "reason": reason, "vouchers_cancelled": affected})
    db.commit()
    return {"status": "success", "batch_id": batch.id, "vouchers_cancelled": affected}


def _batch_counts(db: Session, batch_ids: List[int]) -> Dict[int, Dict[str, int]]:
    rows = db.query(Voucher.batch_id, Voucher.status, func.count(Voucher.id)) \
        .filter(Voucher.batch_id.in_(batch_ids)).group_by(Voucher.batch_id, Voucher.status).all() if batch_ids else []
    out: Dict[int, Dict[str, int]] = {}
    for bid, st, n in rows:
        out.setdefault(bid, {})[st] = n
    return out


def serialize_batches(db: Session, batches: List[VoucherBatch]) -> List[Dict[str, Any]]:
    counts = _batch_counts(db, [b.id for b in batches])
    res = []
    for b in batches:
        c = counts.get(b.id, {})
        used = c.get("UTILIZADO", 0)
        incidents = sum(c.get(s, 0) for s in INCIDENT_STATUSES)
        available = c.get("DISTRIBUIDO", 0) + c.get("EMITIDO", 0)
        res.append({
            "id": b.id,
            "batch_number": b.batch_number,
            "campaign_id": b.campaign_id,
            "campaign_name": b.campaign.name if b.campaign else "",
            "box_id": b.box_id,
            "box_number": b.box.box_number if b.box else "",
            "permissionario_id": b.permissionario_id,
            "permissionario_name": b.permissionario.name if b.permissionario else "",
            "code_prefix": b.code_prefix,
            "first_code": f"{b.code_prefix}-{b.start_number:05d}",
            "last_code": f"{b.code_prefix}-{b.end_number:05d}",
            "total": b.total_vouchers,
            "issued": c.get("EMITIDO", 0),
            "used": used,
            "available": available,
            "incidents": incidents,
            "status": b.status,
            "distributed_at": b.distributed_at.isoformat() if b.distributed_at else None,
            "distributed_by": b.distributed_by.full_name if b.distributed_by else "Carga inicial",
            "notes": b.notes,
            "cancel_reason": b.cancel_reason,
        })
    return res


def list_batches(db: Session, campaign_id: Optional[int] = None, permissionario_id: Optional[int] = None,
                 q: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(VoucherBatch)
    if campaign_id:
        query = query.filter(VoucherBatch.campaign_id == campaign_id)
    if permissionario_id:
        query = query.filter(VoucherBatch.permissionario_id == permissionario_id)
    items = serialize_batches(db, query.order_by(VoucherBatch.id.desc()).all())
    if q:
        ql = q.strip().lower()
        items = [i for i in items if ql in i["box_number"].lower() or ql in i["permissionario_name"].lower()
                 or ql in i["code_prefix"].lower() or ql == str(i["batch_number"])]
    return items


def batch_history(db: Session, batch_id: int) -> List[Dict[str, Any]]:
    logs = db.query(AuditLog).filter(AuditLog.entity_name == "VoucherBatch", AuditLog.entity_id == str(batch_id)) \
        .order_by(AuditLog.id.asc()).all()
    voucher_ids = [str(v.id) for v in db.query(Voucher.id).filter(Voucher.batch_id == batch_id).all()]
    if voucher_ids:
        logs += db.query(AuditLog).filter(AuditLog.entity_name == "Voucher", AuditLog.entity_id.in_(voucher_ids)) \
            .order_by(AuditLog.id.asc()).all()
    logs.sort(key=lambda l: l.id)
    return [{"timestamp": l.created_at.isoformat(), "username": l.username or "SISTEMA", "action": l.action,
             "after": json.loads(l.after_state_json) if l.after_state_json else None} for l in logs]


def normalize_code(code: str) -> str:
    """Aceita o código digitado, lido do QR (URL ou texto) ou sem hífen: 'natal 1' -> NATAL-00001."""
    raw = (code or "").strip().upper()
    if "/" in raw:  # QR com URL de consulta
        raw = raw.rstrip("/").split("/")[-1]
    m = re.match(r"^([A-Z0-9]{2,10}?)[\s\-_]*0*(\d{1,5})$", raw)
    if m and not raw[: len(m.group(1))].isdigit():
        return f"{m.group(1)}-{int(m.group(2)):05d}"
    return raw


def query_voucher_by_code(db: Session, code: str) -> Optional[Dict[str, Any]]:
    norm_code = normalize_code(code)
    v = db.query(Voucher).filter(Voucher.full_code == norm_code).first()
    if not v:
        v = db.query(Voucher).filter(Voucher.digital_qr_token == (code or "").strip().upper()).first()
    if not v:
        return None
    part = v.participation
    perm = v.permissionario
    camp = v.batch.campaign if v.batch else None
    return {
        "id": v.id,
        "full_code": v.full_code,
        "sequence_number": v.sequence_number,
        "status": v.status,
        "status_label": VOUCHER_STATUS_LABELS.get(v.status, v.status),
        "campaign_id": v.campaign_id,
        "campaign_name": camp.name if camp else "",
        "campaign_status": camp.status if camp else None,
        "box_id": v.box_id,
        "box_number": v.box.box_number if v.box else "",
        "permissionario_id": v.permissionario_id,
        "permissionario_name": perm.name if perm else "",
        "permissionario_status": perm.status if perm else None,
        "batch_id": v.batch_id,
        "batch_number": v.batch.batch_number if v.batch else None,
        "batch_status": v.batch.status if v.batch else None,
        "issued_at": v.issued_at.isoformat() if v.issued_at else None,
        "issued_value": v.issued_value,
        "invoice_doc_number": v.invoice_doc_number,
        "is_used": v.status == "UTILIZADO",
        "participation": {
            "lucky_number": part.lucky_number,
            "validated_at": part.validated_at.isoformat(),
            "participant_name": part.participant.full_name,
            "participant_cpf_masked": mask_cpf(part.participant.document_cpf),
            "attendant": part.attendant.full_name if part.attendant else None,
        } if part else None,
    }


def eligibility(db: Session, campaign_id: int, code: str) -> Dict[str, Any]:
    """Pré-checagem para o balcão: diz se o comprovante pode virar participação e por quê."""
    info = query_voucher_by_code(db, code)
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    def r(ok, kind, message):
        return {"ok": ok, "kind": kind, "message": message, "voucher": info}
    if not campaign:
        return r(False, "ERRO", "Campanha não encontrada.")
    if campaign.status != "ATIVA":
        return r(False, "CAMPANHA_ENCERRADA", "A campanha selecionada não está ativa.")
    if datetime.utcnow() > campaign.registration_end_date:
        return r(False, "CAMPANHA_ENCERRADA", "O prazo de cadastro de comprovantes desta campanha terminou.")
    if not info:
        return r(False, "INEXISTENTE", f"Comprovante {normalize_code(code)} não existe no sistema.")
    if info["campaign_id"] != campaign_id:
        return r(False, "OUTRA_CAMPANHA", f"Este comprovante pertence a outra campanha ({info['campaign_name']}).")
    if info["status"] == "UTILIZADO":
        p = info["participation"]
        return r(False, "JA_UTILIZADO", f"Já utilizado: gerou o número {p['lucky_number']} em "
                                        f"{p['validated_at'][:10]}.")
    if info["status"] in INCIDENT_STATUSES:
        return r(False, "CANCELADO", f"Comprovante {VOUCHER_STATUS_LABELS[info['status']].lower()}. Não pode ser usado.")
    if info["permissionario_status"] != "ATIVO":
        return r(False, "PERMISSIONARIO_IRREGULAR",
                 f"O permissionário do box {info['box_number']} está com cadastro {info['permissionario_status']}.")
    return r(True, "VALIDO", f"Comprovante válido. Box {info['box_number']} — {info['permissionario_name']}.")
