"""Autenticação, sessão e gestão de usuários."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.entities import User, Permissionario
from app.core.security import hash_password, verify_password, login_limiter, MIN_PASSWORD_LENGTH
from app.core.exceptions import DomainRuleException
from app.services.audit_service import log_audit

VALID_ROLES = {"ADMIN", "ATENDENTE", "PERMISSIONARIO"}


def authenticate_user(db: Session, username: str, plain_password: str, ip: Optional[str] = None) -> User:
    key = f"{(username or '').strip().lower()}|{ip or '-'}"
    wait = login_limiter.check(key)
    if wait:
        raise DomainRuleException(
            f"Muitas tentativas sem sucesso. Aguarde {wait} segundos e tente novamente.", status_code=429
        )
    user = db.query(User).filter(User.username == (username or "").strip()).first()
    if not user or not user.is_active or not verify_password(plain_password, user.password_hash):
        login_limiter.fail(key)
        log_audit(db, "LOGIN_FAILED", "User", entity_id=user.id if user else None,
                  username=(username or "")[:64], ip_address=ip)
        db.commit()
        raise DomainRuleException("Usuário ou senha incorretos.", status_code=401)
    login_limiter.reset(key)
    user.last_login_at = datetime.utcnow()
    log_audit(db, "LOGIN", "User", entity_id=user.id, user_id=user.id, username=user.username, ip_address=ip)
    db.commit()
    db.refresh(user)
    return user


def logout_user(db: Session, user_id: int):
    """Invalida todas as sessões do usuário (incrementa a versão do token)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.token_version = (user.token_version or 0) + 1
        log_audit(db, "LOGOUT", "User", entity_id=user.id, user_id=user.id, username=user.username)
        db.commit()


def change_password(db: Session, user_id: int, current: str, new: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(current, user.password_hash):
        raise DomainRuleException("Senha atual incorreta.", status_code=400)
    if user.is_demo:
        raise DomainRuleException("Contas de demonstração não podem ter a senha alterada.")
    if len(new) < MIN_PASSWORD_LENGTH:
        raise DomainRuleException(f"A nova senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.")
    user.password_hash = hash_password(new)
    user.token_version = (user.token_version or 0) + 1
    log_audit(db, "PASSWORD_CHANGED", "User", entity_id=user.id, user_id=user.id, username=user.username)
    db.commit()
    db.refresh(user)
    return user


def create_user(
    db: Session,
    username: str,
    password: str,
    full_name: str,
    role: str,
    permissionario_id: Optional[int] = None,
    created_by_user_id: Optional[int] = None,
    created_by_username: Optional[str] = None,
) -> User:
    username = username.strip()
    if role not in VALID_ROLES:
        raise DomainRuleException("Perfil inválido.")
    if db.query(User).filter(User.username == username).first():
        raise DomainRuleException(f"O usuário '{username}' já existe.", status_code=409)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DomainRuleException(f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.")
    if role == "PERMISSIONARIO":
        if not permissionario_id or not db.query(Permissionario).filter(Permissionario.id == permissionario_id).first():
            raise DomainRuleException("Usuários do portal precisam estar vinculados a um permissionário.")
    else:
        permissionario_id = None

    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role=role,
        permissionario_id=permissionario_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_audit(db, "USER_CREATED", "User", entity_id=user.id, user_id=created_by_user_id,
              username=created_by_username,
              after_state={"username": username, "full_name": full_name, "role": role,
                           "permissionario_id": permissionario_id})
    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, target_id: int, active: bool, actor_id: int, actor_username: str) -> User:
    user = db.query(User).filter(User.id == target_id).first()
    if not user:
        raise DomainRuleException("Usuário não encontrado.", status_code=404)
    if user.id == actor_id and not active:
        raise DomainRuleException("Você não pode desativar a sua própria conta.")
    before = user.is_active
    user.is_active = active
    user.token_version = (user.token_version or 0) + 1
    log_audit(db, "USER_ACTIVATED" if active else "USER_DEACTIVATED", "User", entity_id=user.id,
              user_id=actor_id, username=actor_username,
              before_state={"is_active": before}, after_state={"is_active": active})
    db.commit()
    db.refresh(user)
    return user
