"""Phase 5: Counter attendance, participant registration, atomic voucher validation, and lucky number issuance."""
import re
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, update, select
from sqlalchemy.exc import IntegrityError
from app.models.entities import (
    Voucher,
    Campaign,
    Participant,
    Participation,
    ValidationAttempt,
    Box,
    Permissionario,
)
from app.core.exceptions import (
    DomainRuleException,
    VoucherAlreadyUsedException,
    VoucherNotEligibleException,
    CampaignNotActiveException,
)
from app.services.audit_service import log_audit, mask_cpf
from app.services.voucher_service import normalize_code

def normalize_cpf(cpf_raw: str) -> str:
    """Strip all non-digit characters and ensure 11 digits."""
    cleaned = re.sub(r"\D", "", cpf_raw or "")
    if len(cleaned) != 11:
        raise DomainRuleException("O CPF informado deve conter exatamente 11 dígitos numéricos.")
    return cleaned

_LOWER_PARTICLES = {"da", "de", "do", "das", "dos", "e"}


def format_name(name: str) -> str:
    """'MARIA DO SOCORRO' -> 'Maria do Socorro' (partículas em minúsculas)."""
    words = (name or "").strip().split()
    return " ".join(w.lower() if i and w.lower() in _LOWER_PARTICLES else w.capitalize() for i, w in enumerate(words))


def get_or_create_participant(
    db: Session,
    cpf: str,
    name: str,
    phone: str,
    email: Optional[str] = None,
    neighborhood: Optional[str] = None,
) -> Participant:
    """Find participant by CPF or register a new one."""
    norm_cpf = normalize_cpf(cpf)
    participant = db.query(Participant).filter(Participant.document_cpf == norm_cpf).first()
    if not participant:
        participant = Participant(
            document_cpf=norm_cpf,
            full_name=format_name(name),
            phone=phone.strip(),
            email=email.strip().lower() if email else None,
            neighborhood=format_name(neighborhood) if neighborhood else None,
        )
        db.add(participant)
        db.flush()
    else:
        # Update contact info if provided
        if phone:
            participant.phone = phone.strip()
        if neighborhood:
            participant.neighborhood = format_name(neighborhood)
        if email:
            participant.email = email.strip().lower()
        db.flush()
    return participant

def _refuse(db, campaign_id, code, user_id, cpf, reason, ip, exc_cls=None, kind="RECUSA"):
    _record_attempt(db, campaign_id, code, user_id, cpf, False, f"{reason}", ip)
    db.commit()
    if exc_cls is VoucherAlreadyUsedException:
        raise VoucherAlreadyUsedException(code)
    raise VoucherNotEligibleException(reason)


def _next_lucky_number(db: Session, campaign_id: int) -> int:
    """Reserva o próximo número da sorte com um UPDATE atômico no contador da campanha.

    Duas validações simultâneas nunca recebem o mesmo número: o banco serializa o UPDATE.
    """
    db.execute(
        update(Campaign).where(Campaign.id == campaign_id)
        .values(lucky_number_seq=Campaign.lucky_number_seq + 1)
    )
    return db.execute(select(Campaign.lucky_number_seq).where(Campaign.id == campaign_id)).scalar_one()


def validate_and_issue_participation(
    db: Session,
    campaign_id: int,
    voucher_code: str,
    participant_cpf: str,
    participant_name: str,
    participant_phone: str,
    attendant_user_id: int,
    attendant_username: str,
    participant_neighborhood: Optional[str] = None,
    participant_email: Optional[str] = None,
    consent_lgpd: bool = True,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Valida o comprovante e emite exatamente um número da sorte, de forma atômica."""
    norm_code = normalize_code(voucher_code)
    norm_cpf = normalize_cpf(participant_cpf)
    if not is_valid_cpf(norm_cpf):
        raise DomainRuleException("CPF inválido: os dígitos verificadores não conferem.", status_code=422)
    if not (participant_name or "").strip() or len(participant_name.strip()) < 3:
        raise DomainRuleException("Informe o nome completo do participante.", status_code=422)
    phone_digits = re.sub(r"\D", "", participant_phone or "")
    if len(phone_digits) < 10:
        raise DomainRuleException("Informe um telefone com DDD.", status_code=422)
    if not consent_lgpd:
        raise DomainRuleException("É necessário o consentimento do participante para o tratamento dos dados.", status_code=422)

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise DomainRuleException("Campanha especificada não existe.", status_code=404)
    if campaign.status != "ATIVA":
        raise CampaignNotActiveException(campaign.status)

    if datetime.utcnow() > campaign.registration_end_date:
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                "Prazo para cadastro de comprovantes nesta campanha já foi encerrado.", ip_address)

    voucher = db.query(Voucher).filter(Voucher.full_code == norm_code).first()
    if not voucher:
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"Comprovante '{norm_code}' não existe no sistema.", ip_address)
    if voucher.campaign_id != campaign_id:
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"O comprovante '{norm_code}' pertence a outra campanha.", ip_address)
    if voucher.status in ["CANCELADO", "EXTRAVIADO", "DEVOLVIDO"]:
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"Comprovante inválido para uso (situação: {voucher.status}).", ip_address)
    if voucher.status == "UTILIZADO":
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"Comprovante '{norm_code}' já foi utilizado e validado anteriormente.", ip_address,
                exc_cls=VoucherAlreadyUsedException)
    perm = voucher.permissionario
    if not perm or perm.status != "ATIVO":
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"Permissionário do box com cadastro irregular ({perm.status if perm else 'inexistente'}).", ip_address)
    if voucher.issued_value is not None and voucher.issued_value < campaign.min_purchase_value:
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"Valor da compra (R$ {voucher.issued_value:.2f}) abaixo do mínimo da campanha "
                f"(R$ {campaign.min_purchase_value:.2f}).", ip_address)

    participant = get_or_create_participant(db, norm_cpf, participant_name, participant_phone,
                                            email=participant_email, neighborhood=participant_neighborhood)
    existing_count = db.query(Participation).filter(Participation.campaign_id == campaign_id,
                                                    Participation.participant_id == participant.id).count()
    if existing_count >= campaign.max_numbers_per_cpf:
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"Limite máximo de {campaign.max_numbers_per_cpf} números da sorte atingido para este CPF.", ip_address)

    # Trava atômica: só uma requisição consegue mudar o comprovante para UTILIZADO.
    updated_rows = (
        db.query(Voucher)
        .filter(Voucher.id == voucher.id, Voucher.status.in_(["DISTRIBUIDO", "EMITIDO"]))
        .update({"status": "UTILIZADO", "updated_at": datetime.utcnow()}, synchronize_session="fetch")
    )
    if updated_rows == 0:
        db.rollback()
        _refuse(db, campaign_id, norm_code, attendant_user_id, norm_cpf,
                f"Comprovante '{norm_code}' já foi utilizado e validado anteriormente.", ip_address,
                exc_cls=VoucherAlreadyUsedException)

    seq = _next_lucky_number(db, campaign_id)
    if seq > 99999:
        db.rollback()
        raise DomainRuleException("Limite de 99.999 números da sorte atingido nesta campanha.", status_code=409)
    lucky_number = f"{seq:05d}"

    participation = Participation(
        campaign_id=campaign_id, voucher_id=voucher.id, participant_id=participant.id, box_id=voucher.box_id,
        permissionario_id=voucher.permissionario_id, attendant_user_id=attendant_user_id,
        lucky_number=lucky_number, validated_at=datetime.utcnow(),
    )
    db.add(participation)
    _record_attempt(db, campaign_id, norm_code, attendant_user_id, norm_cpf, True, None, ip_address)
    log_audit(db=db, action="PARTICIPATION_VALIDATED", entity_name="Voucher", entity_id=voucher.id,
              user_id=attendant_user_id, username=attendant_username, campaign_id=campaign_id,
              after_state={"voucher_code": norm_code, "lucky_number": lucky_number,
                           "participant_cpf": mask_cpf(norm_cpf), "box_id": voucher.box_id})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainRuleException("Conflito ao registrar a participação. Tente novamente.", status_code=409)
    db.refresh(participation)

    return {
        "status": "success",
        "message": "Participação validada com sucesso!",
        "lucky_number": lucky_number,
        "participation_id": participation.id,
        "campaign": {"id": campaign.id, "name": campaign.name},
        "participant": {
            "name": participant.full_name,
            "cpf": participant.document_cpf,
            "cpf_masked": mask_cpf(participant.document_cpf),
            "total_tickets_in_campaign": existing_count + 1,
            "remaining_in_campaign": campaign.max_numbers_per_cpf - existing_count - 1,
        },
        "voucher": {
            "code": voucher.full_code,
            "box_number": voucher.box.box_number if voucher.box else "",
            "permissionario": perm.name if perm else "",
        },
        "validated_at": participation.validated_at.isoformat(),
    }


def is_valid_cpf(cpf: str) -> bool:
    """Confere os dígitos verificadores do CPF (rejeita sequências repetidas)."""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for n in (9, 10):
        total = sum(int(cpf[i]) * ((n + 1) - i) for i in range(n))
        digit = (total * 10) % 11 % 10
        if digit != int(cpf[n]):
            return False
    return True


def find_participant(db: Session, cpf_raw: str, campaign_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Recupera dados de um consumidor já cadastrado para agilizar o balcão."""
    try:
        cpf = normalize_cpf(cpf_raw)
    except DomainRuleException:
        return None
    p = db.query(Participant).filter(Participant.document_cpf == cpf).first()
    if not p:
        return None
    count = 0
    if campaign_id:
        count = db.query(Participation).filter(Participation.participant_id == p.id,
                                               Participation.campaign_id == campaign_id).count()
    return {"name": p.full_name, "phone": p.phone, "email": p.email, "neighborhood": p.neighborhood,
            "numbers_in_campaign": count}


def _record_attempt(
    db: Session,
    campaign_id: Optional[int],
    voucher_code: str,
    user_id: Optional[int],
    cpf: Optional[str],
    success: bool,
    reason: Optional[str],
    ip: Optional[str],
):
    """Internal helper to persist a validation attempt."""
    attempt = ValidationAttempt(
        campaign_id=campaign_id,
        voucher_code=voucher_code,
        tried_by_user_id=user_id,
        participant_cpf=cpf,
        success=success,
        refusal_reason=reason,
        ip_address=ip,
    )
    db.add(attempt)
    db.flush()
