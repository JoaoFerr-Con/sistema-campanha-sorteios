"""Phase 6: Authenticated Permissionário Portal with strict isolation and IDOR protection."""
import secrets
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import Permissionario, BoxOccupancy, VoucherBatch, Voucher, Box, Participation, Campaign
from app.core.exceptions import DomainRuleException
from app.services.audit_service import log_audit

def get_permissionario_or_raise(db: Session, permissionario_id: int) -> Permissionario:
    """Ensure permissionario exists and is active."""
    perm = db.query(Permissionario).filter(Permissionario.id == permissionario_id).first()
    if not perm:
        raise DomainRuleException("Cadastro de permissionário não encontrado.", status_code=404)
    if perm.status != "ATIVO":
        raise DomainRuleException(f"Acesso operacional bloqueado: cadastro com situação '{perm.status}'.", status_code=403)
    return perm

def get_portal_overview(db: Session, permissionario_id: int) -> Dict[str, Any]:
    """Visão do portal restrita ao permissionário autenticado (consulta liberada mesmo se irregular)."""
    perm = db.query(Permissionario).filter(Permissionario.id == permissionario_id).first()
    if not perm:
        raise DomainRuleException("Cadastro de permissionário não encontrado.", status_code=404)

    # Active boxes linked to this permissionario
    occupancies = (
        db.query(BoxOccupancy)
        .filter(BoxOccupancy.permissionario_id == permissionario_id, BoxOccupancy.is_current == True)
        .all()
    )

    boxes_data = []
    for occ in occupancies:
        boxes_data.append({
            "box_id": occ.box_id,
            "box_number": occ.box.box_number,
            "activity": occ.activity_name,
            "official_status": occ.box.official_status,
            "start_date": occ.start_date.isoformat(),
        })

    from app.services.voucher_service import list_batches
    batches_data = list_batches(db, permissionario_id=permissionario_id)

    parts = (db.query(Participation).filter(Participation.permissionario_id == permissionario_id)
             .order_by(Participation.id.desc()).limit(50).all())
    total_parts = db.query(Participation).filter(Participation.permissionario_id == permissionario_id).count()
    active_campaigns = db.query(Campaign).filter(Campaign.status == "ATIVA").all()

    return {
        "permissionario": {
            "id": perm.id,
            "name": perm.name,
            "document_masked": ("***" + perm.document_cpf_cnpj[-4:]) if perm.document_cpf_cnpj else None,
            "sebrae_level": perm.sebrae_qualification_level,
            "status": perm.status,
        },
        "linked_boxes": boxes_data,
        "batches": batches_data,
        "totals": {
            "total": sum(b["total"] for b in batches_data),
            "available": sum(b["available"] for b in batches_data),
            "issued": sum(b["issued"] for b in batches_data),
            "used": sum(b["used"] for b in batches_data),
            "incidents": sum(b["incidents"] for b in batches_data),
            "participations": total_parts,
        },
        "active_campaigns": [{"id": c.id, "name": c.name, "purchase_end_date": c.purchase_end_date.isoformat(),
                              "registration_end_date": c.registration_end_date.isoformat(),
                              "min_purchase_value": c.min_purchase_value} for c in active_campaigns],
        "recent_participations": [{"lucky_number": p.lucky_number, "voucher_code": p.voucher.full_code,
                                   "validated_at": p.validated_at.isoformat(),
                                   "campaign_id": p.campaign_id} for p in parts],
    }

def issue_voucher_by_permissionario(
    db: Session,
    permissionario_id: int,
    voucher_code: str,
    issued_value: float,
    user_id: int,
    username: str,
    invoice_doc_number: Optional[str] = None,
) -> Dict[str, Any]:
    """Permissionário issues a distributed voucher for a customer purchase."""
    perm = get_permissionario_or_raise(db, permissionario_id)
    norm_code = voucher_code.strip().upper()

    voucher = db.query(Voucher).filter(Voucher.full_code == norm_code).first()
    if not voucher:
        raise DomainRuleException(f"Comprovante '{norm_code}' não encontrado.", status_code=404)

    # Strict isolation check: Voucher must belong to this permissionário
    if voucher.permissionario_id != permissionario_id:
        raise DomainRuleException("Violação de isolamento: este comprovante não pertence ao seu lote.", status_code=403)

    if voucher.status != "DISTRIBUIDO":
        raise DomainRuleException(
            f"Não é possível emitir: comprovante já se encontra na situação '{voucher.status}'."
        )

    campaign = voucher.batch.campaign
    now = datetime.utcnow()
    if campaign.status != "ATIVA":
        raise DomainRuleException("A campanha deste comprovante não está ativa.")
    if not (campaign.purchase_start_date <= now <= campaign.purchase_end_date):
        raise DomainRuleException("Fora do período de compras da campanha.")
    if issued_value < campaign.min_purchase_value:
        raise DomainRuleException(
            f"O valor mínimo de compra nesta campanha é R$ {campaign.min_purchase_value:.2f}.")

    # Generate tamper-resistant digital QR token (e.g. for customer mobile scanning / counter presentation)
    qr_token = secrets.token_hex(16).upper()

    voucher.status = "EMITIDO"
    voucher.issued_at = datetime.utcnow()
    voucher.issued_value = issued_value
    voucher.invoice_doc_number = invoice_doc_number.strip() if invoice_doc_number else None
    voucher.digital_qr_token = qr_token

    log_audit(
        db=db,
        action="VOUCHER_ISSUED_BY_MERCHANT",
        entity_name="Voucher",
        entity_id=voucher.id,
        user_id=user_id,
        username=username,
        campaign_id=voucher.campaign_id,
        after_state={"code": norm_code, "value": issued_value, "invoice": invoice_doc_number},
    )

    db.commit()
    db.refresh(voucher)

    return {
        "status": "success",
        "message": f"Comprovante {norm_code} emitido com sucesso!",
        "voucher_code": voucher.full_code,
        "issued_value": voucher.issued_value,
        "digital_qr_token": qr_token,
        "issued_at": voucher.issued_at.isoformat(),
    }

def report_voucher_incident(
    db: Session,
    permissionario_id: int,
    voucher_code: str,
    target_status: str,
    reason: str,
    user_id: int,
    username: str,
) -> Dict[str, Any]:
    """Report voucher loss, cancellation, or return."""
    perm = get_permissionario_or_raise(db, permissionario_id)
    norm_code = voucher_code.strip().upper()

    voucher = db.query(Voucher).filter(Voucher.full_code == norm_code).first()
    if not voucher:
        raise DomainRuleException(f"Comprovante '{norm_code}' não encontrado.", status_code=404)

    if voucher.permissionario_id != permissionario_id:
        raise DomainRuleException("Violação de isolamento: este comprovante não pertence ao seu lote.", status_code=403)

    if voucher.status == "UTILIZADO":
        raise DomainRuleException("Comprovante já foi validado em participação e não pode ser alterado.", status_code=400)
    if voucher.status in ("EXTRAVIADO", "DEVOLVIDO", "CANCELADO"):
        raise DomainRuleException(f"Este comprovante já está registrado como {voucher.status}.", status_code=400)

    before_status = voucher.status
    voucher.status = target_status

    log_audit(
        db=db,
        action=f"VOUCHER_INCIDENT_{target_status}",
        entity_name="Voucher",
        entity_id=voucher.id,
        user_id=user_id,
        username=username,
        campaign_id=voucher.campaign_id,
        before_state={"status": before_status},
        after_state={"status": target_status, "reason": reason},
    )

    db.commit()
    db.refresh(voucher)

    return {
        "status": "success",
        "message": f"Comprovante {norm_code} atualizado para a situação '{target_status}'.",
        "previous_status": before_status,
        "current_status": voucher.status,
    }
