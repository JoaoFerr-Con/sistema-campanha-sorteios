"""Configuração da aplicação, lida de variáveis de ambiente.

Modos de execução
-----------------
* DEMO_MODE=true (padrão): cria contas e uma campanha piloto de demonstração,
  com senhas conhecidas exibidas na tela de login. Use apenas para homologação.
* DEMO_MODE=false: nenhuma conta de demonstração é criada. O administrador
  inicial vem de ADMIN_USERNAME / ADMIN_PASSWORD e SECRET_KEY é obrigatório.

Banco de dados
--------------
* DATABASE_URL definido: usa esse banco (ex.: Postgres do Neon/Supabase).
* Na Vercel sem DATABASE_URL: SQLite em /tmp (temporário — é apagado quando a
  função reinicia). Adequado somente para demonstração.
* Localmente sem DATABASE_URL: SQLite no arquivo sistema_campanhas.db.
"""
import os
import secrets
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
EXCEL_FILENAME = "Permissionarios_Box_Nome_Atividade.xlsx"

IS_VERCEL = bool(os.getenv("VERCEL"))


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        # Provedores costumam entregar "postgres://"; o SQLAlchemy exige o driver explícito.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url
    if IS_VERCEL:
        return "sqlite:////tmp/sistema_campanhas.db"
    return f"sqlite:///{BASE_DIR / 'sistema_campanhas.db'}"


DEMO_MODE = _bool_env("DEMO_MODE", True)
_secret = os.getenv("SECRET_KEY", "").strip()
if not _secret:
    if not DEMO_MODE:
        raise RuntimeError("SECRET_KEY é obrigatório quando DEMO_MODE=false.")
    # Em demonstração, uma chave aleatória por processo: tokens deixam de valer ao reiniciar.
    _secret = secrets.token_urlsafe(48)


class Settings(BaseModel):
    app_name: str = "Campanhas e Sorteios — Complexo Comercial de Barcarena"
    app_version: str = "2.0.0"
    database_url: str = _database_url()
    secret_key: str = _secret
    token_expire_hours: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "10"))
    demo_mode: bool = DEMO_MODE
    is_vercel: bool = IS_VERCEL
    admin_username: str = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    login_max_attempts: int = 5
    login_window_seconds: int = 300
    max_vouchers_per_batch: int = 5000
    data_dir: Path = DATA_DIR
    excel_filename: str = EXCEL_FILENAME

    @property
    def is_ephemeral_db(self) -> bool:
        return self.database_url.startswith("sqlite:////tmp")


settings = Settings()
