"""Senhas (PBKDF2), tokens assinados (HMAC-SHA256), RBAC e limitação de tentativas de login."""
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

ITERATIONS = 240_000
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2:sha256:{ITERATIONS}${base64.b64encode(salt).decode('ascii')}${base64.b64encode(key).decode('ascii')}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        prefix, salt_b64, key_b64 = hashed_password.split("$")
        iters = int(prefix.split(":")[2])
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_key = base64.b64decode(key_b64.encode("ascii"))
        derived_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iters)
        return hmac.compare_digest(derived_key, expected_key)
    except Exception:
        return False


def _sign(data: str) -> str:
    return hmac.new(settings.secret_key.encode("utf-8"), data.encode("ascii"), hashlib.sha256).hexdigest()


def create_access_token(
    user_id: int,
    username: str,
    role: str,
    permissionario_id: Optional[int] = None,
    token_version: int = 0,
) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "permissionario_id": permissionario_id,
        "tv": token_version,
        "exp": int(time.time()) + (settings.token_expire_hours * 3600),
        "nonce": secrets.token_hex(8),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return f"{encoded}.{_sign(encoded)}"


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> dict:
    try:
        encoded, signature = token.split(".")
    except ValueError:
        raise _unauthorized("Sessão inválida. Entre novamente.")
    if not hmac.compare_digest(signature, _sign(encoded)):
        raise _unauthorized("Sessão inválida. Entre novamente.")
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8"))
    except Exception:
        raise _unauthorized("Sessão inválida. Entre novamente.")
    if payload.get("exp", 0) < int(time.time()):
        raise _unauthorized("Sua sessão expirou. Entre novamente.")
    return payload


def get_current_user_payload(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """Valida o token E confirma no banco que o usuário existe, está ativo e não encerrou a sessão.

    A autorização depende exclusivamente desta identidade autenticada — o perfil
    nunca é lido de parâmetros enviados pelo navegador.
    """
    from app.models.entities import User  # import tardio evita ciclo

    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Entre no sistema para continuar.")
    payload = decode_access_token(authorization[7:].strip())
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or not user.is_active:
        raise _unauthorized("Usuário inativo ou inexistente.")
    if (user.token_version or 0) != payload.get("tv", 0):
        raise _unauthorized("Sessão encerrada. Entre novamente.")
    # Valores atuais do banco prevalecem sobre os do token.
    payload["role"] = user.role
    payload["permissionario_id"] = user.permissionario_id
    payload["username"] = user.username
    return payload


def require_roles(allowed_roles: List[str]):
    def role_checker(payload: dict = Depends(get_current_user_payload)) -> dict:
        if payload.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem acesso a esta operação.",
            )
        return payload
    return role_checker


require_authenticated = get_current_user_payload


class LoginRateLimiter:
    """Limita tentativas de login malsucedidas por usuário+IP numa janela de tempo.

    Em ambiente serverless o contador é por instância; para produção com várias
    instâncias, use também a proteção de borda da Vercel (WAF / rate limit).
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float):
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def check(self, key: str) -> Optional[int]:
        """Retorna segundos de espera se bloqueado, senão None."""
        now = time.time()
        with self._lock:
            q = self._prune(key, now)
            if len(q) >= self.max_attempts:
                return int(self.window - (now - q[0])) + 1
        return None

    def fail(self, key: str):
        with self._lock:
            self._hits[key].append(time.time())

    def reset(self, key: str):
        with self._lock:
            self._hits.pop(key, None)


login_limiter = LoginRateLimiter(settings.login_max_attempts, settings.login_window_seconds)
