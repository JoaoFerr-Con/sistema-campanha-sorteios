"""Inicialização do banco: criação de tabelas e dados iniciais.

* Produção (DEMO_MODE=false): cria somente o administrador definido em
  ADMIN_USERNAME / ADMIN_PASSWORD, caso ainda não exista nenhum administrador.
* Demonstração: cria três contas marcadas como demonstração, uma campanha
  piloto e carrega a planilha oficial na área de conferência (staging).
"""
import json
import logging
import threading
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.entities import (
    User, Box, Permissionario, BoxOccupancy, Campaign, CampaignPrize, VoucherBatch, Voucher,
    ImportStagingRow,
)

log = logging.getLogger("campanhas.seed")
DEMO_PASSWORD = "password123"
DEMO_ACCOUNTS = [
    {"username": "admin", "full_name": "Gestão SEICOMTEC", "role": "ADMIN",
     "description": "Gestor: campanhas, cadastros, apuração e auditoria"},
    {"username": "atendente", "full_name": "Atendente do Balcão Central", "role": "ATENDENTE",
     "description": "Balcão: valida comprovantes e emite números da sorte"},
    {"username": "permissionario_260", "full_name": "Sulamita Ferreira (Box 260)", "role": "PERMISSIONARIO",
     "description": "Portal do permissionário do Box 260"},
]

_init_lock = threading.Lock()
_initialized = False


def ensure_initialized():
    """Cria tabelas e dados iniciais uma única vez por processo (compatível com serverless)."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            if settings.demo_mode:
                bootstrap_initial_data(db, import_staging=True)
            else:
                bootstrap_production_admin(db)
        finally:
            db.close()
        _initialized = True


def bootstrap_production_admin(db: Session):
    if db.query(User).filter(User.role == "ADMIN").first():
        return
    if not settings.admin_username or len(settings.admin_password) < 12:
        log.error("Nenhum administrador cadastrado. Defina ADMIN_USERNAME e ADMIN_PASSWORD (mín. 12 caracteres).")
        return
    db.add(User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        full_name="Administrador",
        role="ADMIN",
        is_active=True,
    ))
    db.commit()


def _ensure_user(db: Session, username: str, full_name: str, role: str, permissionario_id=None):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=full_name,
            role=role,
            permissionario_id=permissionario_id,
            is_active=True,
            is_demo=True,
        )
        db.add(user)
        db.flush()
    return user


def bootstrap_initial_data(db: Session, import_staging: bool = False):
    """Dados de demonstração. Ordem preservada: admin (id 1), atendente (id 2)."""
    _ensure_user(db, "admin", "Gestão SEICOMTEC", "ADMIN")
    _ensure_user(db, "atendente", "Atendente do Balcão Central", "ATENDENTE")

    box_260 = db.query(Box).filter(Box.box_number == "260").first()
    if not box_260:
        box_260 = Box(box_number="260", sector="Setor de salões", official_status="CONFIRMADO",
                      notes="Linha 9 da planilha oficial: Sulamita Ferreira Figueira")
        db.add(box_260)
        db.flush()

    perm_260 = db.query(Permissionario).filter(Permissionario.name == "Sulamita Ferreira Figueira").first()
    if not perm_260:
        perm_260 = Permissionario(name="Sulamita Ferreira Figueira", document_cpf_cnpj="12345678901",
                                  status="ATIVO", sebrae_qualification_level="NIVEL_1_REGULAR")
        db.add(perm_260)
        db.flush()

    if not db.query(BoxOccupancy).filter(BoxOccupancy.box_id == box_260.id, BoxOccupancy.is_current == True).first():
        db.add(BoxOccupancy(box_id=box_260.id, permissionario_id=perm_260.id, activity_name="SALÃO E BARBEARIA",
                            is_current=True, authorization_term_ref="TERMO-2023-BOX260"))

    _ensure_user(db, "permissionario_260", "Sulamita Ferreira (Box 260)", "PERMISSIONARIO", perm_260.id)

    name = "Campanha Piloto — Revitalização do Complexo"
    campaign = db.query(Campaign).filter(Campaign.name == name).first()
    if not campaign:
        now = datetime.utcnow()
        checklist = {k: True for k in [
            "legal_promoter_ok", "participant_compliance_ok", "prizes_funded_ok",
            "rules_approved_ok", "lgpd_declared_ok", "electoral_cleared_ok"]}
        campaign = Campaign(
            name=name,
            description="Campanha de demonstração para conhecer o fluxo completo. Não possui regulamento real.",
            start_date=now - timedelta(days=2),
            end_date=now + timedelta(days=60),
            purchase_start_date=now - timedelta(days=2),
            purchase_end_date=now + timedelta(days=50),
            registration_end_date=now + timedelta(days=55),
            min_purchase_value=20.0,
            max_numbers_per_cpf=50,
            status="ATIVA",
            legal_promoter_name="Prefeitura Municipal de Barcarena — SEICOMTEC",
            legal_promoter_doc="05.105.200/0001-22",
            legal_checklist_json=json.dumps(checklist),
            legal_approval_justification="Aprovação simulada para demonstração.",
            draw_method="LOTERIA_FEDERAL",
            draw_approximation_rule="MAIS_PROXIMO",
            regulation_reference="DEMONSTRAÇÃO — sem regulamento aprovado",
            approved_at=now - timedelta(days=3),
            activated_at=now - timedelta(days=2),
        )
        db.add(campaign)
        db.flush()
        db.add(CampaignPrize(campaign_id=campaign.id, position=1, title="Motocicleta 160 cc 0 km",
                             estimated_value=18000.0, draw_date=now + timedelta(days=61)))

        batch = VoucherBatch(campaign_id=campaign.id, permissionario_id=perm_260.id, box_id=box_260.id,
                             batch_number=1, code_prefix="NATAL", start_number=1, end_number=50,
                             total_vouchers=50, status="ATIVO",
                             notes="Lote piloto para testes de balcão e portal")
        db.add(batch)
        db.flush()
        db.bulk_save_objects([
            Voucher(batch_id=batch.id, campaign_id=campaign.id, box_id=box_260.id,
                    permissionario_id=perm_260.id, full_code=f"NATAL-{seq:05d}",
                    sequence_number=seq, status="DISTRIBUIDO")
            for seq in range(1, 51)
        ])
    db.commit()

    if import_staging and db.query(ImportStagingRow).count() == 0:
        path = settings.data_dir / settings.excel_filename
        if path.exists():
            from app.services.box_service import import_spreadsheet_to_staging
            import_spreadsheet_to_staging(db, path, user_id=None)
    if import_staging:
        from app.core.demo_data import populate_demo
        try:
            populate_demo(db)
        except Exception:  # a demonstração não pode impedir o sistema de subir
            db.rollback()
            log.exception("Falha ao gerar a carga de demonstração")
