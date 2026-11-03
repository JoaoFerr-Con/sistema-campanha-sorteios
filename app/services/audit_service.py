"""Registro de auditoria das operações críticas."""
import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.entities import AuditLog


def log_audit(
    db: Session,
    action: str,
    entity_name: str,
    entity_id: Optional[Any] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    before_state: Optional[Any] = None,
    after_state: Optional[Any] = None,
    ip_address: Optional[str] = None,
    campaign_id: Optional[int] = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        entity_name=entity_name,
        entity_id=str(entity_id) if entity_id is not None else None,
        before_state_json=json.dumps(before_state, default=str, ensure_ascii=False) if before_state is not None else None,
        after_state_json=json.dumps(after_state, default=str, ensure_ascii=False) if after_state is not None else None,
        ip_address=ip_address,
        campaign_id=campaign_id,
    )
    db.add(entry)
    db.flush()
    return entry


def mask_cpf(cpf: Optional[str]) -> str:
    """Mascara CPF no padrão adotado em publicações oficiais: ***.456.789-**."""
    if not cpf or len(cpf) != 11:
        return "—"
    return f"***.{cpf[3:6]}.{cpf[6:9]}-**"
