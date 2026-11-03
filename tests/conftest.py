"""Fixtures com banco isolado. O DATABASE_URL é definido antes de importar a aplicação."""
import os
import pathlib

TEST_DB = pathlib.Path(__file__).parent / "_test_campanhas.db"
for suffix in ("", "-wal", "-shm"):
    p = pathlib.Path(str(TEST_DB) + suffix)
    if p.exists():
        p.unlink()
# TEST_DATABASE_URL permite rodar a suíte contra um Postgres (ex.: postgresql://pg@127.0.0.1:5440/campanhas_test)
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{TEST_DB}"
os.environ["DEMO_MODE"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.core import seed  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_engine():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed.bootstrap_initial_data(db, import_staging=False)
    db.close()
    seed._initialized = True  # evita que o middleware rode o seed de demonstração com a planilha
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(test_db):
    with TestClient(app) as c:
        yield c
