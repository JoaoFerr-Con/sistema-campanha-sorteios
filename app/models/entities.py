"""SQLAlchemy ORM models representing the complete domain for the Barcarena System."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    """User account with role-based access control (ADMIN, ATENDENTE, PERMISSIONARIO)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)  # ADMIN, ATENDENTE, PERMISSIONARIO
    permissionario_id = Column(Integer, ForeignKey("permissionarios.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)  # incrementado ao sair / trocar senha
    is_demo = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    permissionario = relationship("Permissionario", back_populates="user", foreign_keys=[permissionario_id])

class Activity(Base):
    """Economic activity category registered in the Complex."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Box(Base):
    """Commercial box unit in the Complex (spaces 1..368)."""
    __tablename__ = "boxes"

    id = Column(Integer, primary_key=True, index=True)
    box_number = Column(String(32), unique=True, nullable=False, index=True)
    sector = Column(String(128), nullable=True)
    official_status = Column(String(32), default="EM_REGULARIZACAO", nullable=False)
    # CONFIRMADO, VAGO_CONFIRMADO, EM_REGULARIZACAO, SEM_USO
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    occupancies = relationship("BoxOccupancy", back_populates="box", cascade="all, delete-orphan")
    vouchers = relationship("Voucher", back_populates="box")

class Permissionario(Base):
    """Authorized trader operating in a commercial box."""
    __tablename__ = "permissionarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    document_cpf_cnpj = Column(String(32), nullable=True, index=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)
    status = Column(String(32), default="ATIVO", nullable=False)  # ATIVO, SUSPENSO, INATIVO, BLOQUEADO
    sebrae_qualification_level = Column(String(32), default="NIVEL_1_REGULAR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="permissionario", uselist=False)
    occupancies = relationship("BoxOccupancy", back_populates="permissionario", cascade="all, delete-orphan")
    vouchers = relationship("Voucher", back_populates="permissionario")
    batches = relationship("VoucherBatch", back_populates="permissionario")

class BoxOccupancy(Base):
    """Historical and active linkage between Box, Permissionario, and Activity."""
    __tablename__ = "box_occupancies"

    id = Column(Integer, primary_key=True, index=True)
    box_id = Column(Integer, ForeignKey("boxes.id", ondelete="CASCADE"), nullable=False, index=True)
    permissionario_id = Column(Integer, ForeignKey("permissionarios.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_name = Column(String(128), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_date = Column(DateTime, nullable=True)
    is_current = Column(Boolean, default=True, nullable=False)
    authorization_term_ref = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    box = relationship("Box", back_populates="occupancies")
    permissionario = relationship("Permissionario", back_populates="occupancies")

class ImportStagingRow(Base):
    """Staging area preserving raw Excel data and tracking review decisions."""
    __tablename__ = "import_staging_rows"

    id = Column(Integer, primary_key=True, index=True)
    row_number = Column(Integer, nullable=False)
    raw_box_number = Column(String(64), nullable=True)
    raw_permissionario_name = Column(String(255), nullable=True)
    raw_activity = Column(String(128), nullable=True)
    status = Column(String(32), default="PENDENTE_REVISAO", nullable=False)
    # PENDENTE_REVISAO, APROVADO, REJEITADO, CONCILIADO
    discrepancy_flags = Column(Text, default="[]", nullable=False)  # JSON serialized list of detected anomalies
    admin_decision = Column(String(64), nullable=True)
    admin_justification = Column(Text, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Campaign(Base):
    """Promotional campaign with strict status progression and legal approval gates."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    purchase_start_date = Column(DateTime, nullable=False)
    purchase_end_date = Column(DateTime, nullable=False)
    registration_end_date = Column(DateTime, nullable=False)
    min_purchase_value = Column(Float, default=20.0, nullable=False)
    max_numbers_per_cpf = Column(Integer, default=50, nullable=False)
    status = Column(String(32), default="EM_ELABORACAO", nullable=False)
    # EM_ELABORACAO, AGUARDANDO_APROVACAO, APROVADA, ATIVA, ENCERRADA, CANCELADA
    legal_promoter_name = Column(String(160), nullable=True)
    legal_promoter_doc = Column(String(64), nullable=True)
    legal_checklist_json = Column(Text, default="{}", nullable=False)
    # Keys: legal_promoter_ok, participant_compliance_ok, prizes_funded_ok, rules_approved_ok, lgpd_declared_ok, electoral_cleared_ok
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    draw_method = Column(String(64), default="LOTERIA_FEDERAL", nullable=False)
    # Regra de aproximação quando não há número da sorte idêntico ao apurado.
    # Deve reproduzir exatamente o texto do regulamento aprovado (ver DIAGNOSTICO.md).
    draw_approximation_rule = Column(String(48), nullable=True)
    regulation_reference = Column(String(160), nullable=True)  # nº do processo / certificado / ato
    regulation_url = Column(String(255), nullable=True)
    regulation_notes = Column(Text, nullable=True)
    lucky_number_seq = Column(Integer, default=0, nullable=False)  # contador atômico de números da sorte
    legal_approval_justification = Column(Text, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    prizes = relationship("CampaignPrize", back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignPrize.position")
    batches = relationship("VoucherBatch", back_populates="campaign", cascade="all, delete-orphan")
    participations = relationship("Participation", back_populates="campaign", cascade="all, delete-orphan")
    draw_results = relationship("DrawResult", back_populates="campaign", cascade="all, delete-orphan")

class CampaignPrize(Base):
    """Prêmio previsto no regulamento, apurado em ordem de posição."""
    __tablename__ = "campaign_prizes"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    estimated_value = Column(Float, nullable=True)
    draw_date = Column(DateTime, nullable=True)  # data da extração da Loteria Federal vinculada
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="prizes")

    __table_args__ = (UniqueConstraint("campaign_id", "position", name="uq_prize_campaign_position"),)

class VoucherBatch(Base):
    """Batch of vouchers (talão) allocated exclusively to a confirmed box and permissionario."""
    __tablename__ = "voucher_batches"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    permissionario_id = Column(Integer, ForeignKey("permissionarios.id", ondelete="CASCADE"), nullable=False, index=True)
    box_id = Column(Integer, ForeignKey("boxes.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_number = Column(Integer, nullable=False)
    code_prefix = Column(String(32), nullable=False)
    start_number = Column(Integer, nullable=False)
    end_number = Column(Integer, nullable=False)
    total_vouchers = Column(Integer, nullable=False)
    distributed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    distributed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), default="ATIVO", nullable=False)  # ATIVO, CANCELADO, CONCLUIDO
    notes = Column(Text, nullable=True)
    cancel_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="batches")
    box = relationship("Box")
    distributed_by = relationship("User", foreign_keys=[distributed_by_user_id])
    permissionario = relationship("Permissionario", back_populates="batches")
    vouchers = relationship("Voucher", back_populates="batch", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("campaign_id", "code_prefix", "start_number", name="uq_batch_campaign_prefix_start"),
    )

class Voucher(Base):
    """Individual promotional voucher tracked through its entire lifecycle."""
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("voucher_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    box_id = Column(Integer, ForeignKey("boxes.id", ondelete="CASCADE"), nullable=False, index=True)
    permissionario_id = Column(Integer, ForeignKey("permissionarios.id", ondelete="CASCADE"), nullable=False, index=True)
    full_code = Column(String(64), unique=True, nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)
    status = Column(String(32), default="DISTRIBUIDO", nullable=False, index=True)
    # DISTRIBUIDO, EMITIDO, UTILIZADO, CANCELADO, DEVOLVIDO, EXTRAVIADO
    issued_at = Column(DateTime, nullable=True)
    issued_value = Column(Float, nullable=True)
    invoice_doc_number = Column(String(64), nullable=True)
    digital_qr_token = Column(String(64), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    batch = relationship("VoucherBatch", back_populates="vouchers")
    box = relationship("Box", back_populates="vouchers")
    permissionario = relationship("Permissionario", back_populates="vouchers")
    participation = relationship("Participation", back_populates="voucher", uselist=False)

    __table_args__ = (Index("ix_voucher_batch_status", "batch_id", "status"),)

class Participant(Base):
    """Consumer participating in campaign draws."""
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(160), nullable=False)
    document_cpf = Column(String(14), unique=True, nullable=False, index=True)  # Normalized 11 digits
    phone = Column(String(32), nullable=False)
    email = Column(String(128), nullable=True)
    neighborhood = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    participations = relationship("Participation", back_populates="participant")

class ValidationAttempt(Base):
    """Audit record of every counter attempt to validate a voucher (successful or rejected)."""
    __tablename__ = "validation_attempts"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    voucher_code = Column(String(64), nullable=False, index=True)
    tried_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    participant_cpf = Column(String(14), nullable=True)
    success = Column(Boolean, nullable=False)
    refusal_reason = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Participation(Base):
    """Validated participation linking 1 voucher strictly to 1 unique lucky number in a campaign."""
    __tablename__ = "participations"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id", ondelete="RESTRICT"), unique=True, nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id", ondelete="RESTRICT"), nullable=False, index=True)
    box_id = Column(Integer, ForeignKey("boxes.id", ondelete="RESTRICT"), nullable=False)
    permissionario_id = Column(Integer, ForeignKey("permissionarios.id", ondelete="RESTRICT"), nullable=False)
    attendant_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    lucky_number = Column(String(32), nullable=False, index=True)
    validated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="participations")
    voucher = relationship("Voucher", back_populates="participation")
    participant = relationship("Participant", back_populates="participations")

    attendant = relationship("User", foreign_keys=[attendant_user_id])

    __table_args__ = (
        UniqueConstraint("campaign_id", "lucky_number", name="uq_participation_campaign_lucky_number"),
        Index("ix_participation_campaign_participant", "campaign_id", "participant_id"),
    )

class DrawBaseSnapshot(Base):
    """Congelamento formal da base de participações antes da apuração."""
    __tablename__ = "draw_base_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, unique=True)
    participations_count = Column(Integer, nullable=False)
    first_lucky_number = Column(String(32), nullable=True)
    last_lucky_number = Column(String(32), nullable=True)
    sha256 = Column(String(64), nullable=False)
    frozen_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    frozen_by_username = Column(String(64), nullable=True)
    frozen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class DrawResult(Base):
    """Official draw results based on Loteria Federal extraction with audit integrity hash."""
    __tablename__ = "draw_results"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    draw_date = Column(DateTime, nullable=False)
    federal_lottery_contest_number = Column(String(32), nullable=False)
    federal_lottery_extraction_json = Column(Text, nullable=False)
    consolidated_base_sha256 = Column(String(64), nullable=False)
    calculation_rule = Column(String(255), nullable=False)
    winner_lucky_number = Column(String(32), nullable=False)
    winning_participation_id = Column(Integer, ForeignKey("participations.id", ondelete="RESTRICT"), nullable=True)
    prize_id = Column(Integer, ForeignKey("campaign_prizes.id", ondelete="RESTRICT"), nullable=True, index=True)
    prize_title = Column(String(160), nullable=False)
    target_number = Column(String(32), nullable=True)  # número apurado a partir da extração
    match_type = Column(String(16), nullable=True)  # EXATO, APROXIMADO
    approximation_rule = Column(String(48), nullable=True)
    distance = Column(Integer, nullable=True)
    status = Column(String(16), default="VALIDO", nullable=False)  # VALIDO, ANULADO
    executed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    executed_by_username = Column(String(64), nullable=True)
    annulled_reason = Column(Text, nullable=True)
    annulled_by_username = Column(String(64), nullable=True)
    annulled_at = Column(DateTime, nullable=True)
    delivery_status = Column(String(32), default="PENDENTE", nullable=False)  # PENDENTE, CONTATADO, ENTREGUE
    delivery_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="draw_results")
    winning_participation = relationship("Participation")
    prize = relationship("CampaignPrize")
    delivery_events = relationship("PrizeDeliveryEvent", back_populates="draw", cascade="all, delete-orphan", order_by="PrizeDeliveryEvent.id")

class PrizeDeliveryEvent(Base):
    """Histórico de contato e entrega da premiação."""
    __tablename__ = "prize_delivery_events"

    id = Column(Integer, primary_key=True, index=True)
    draw_id = Column(Integer, ForeignKey("draw_results.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False)
    notes = Column(Text, nullable=True)
    username = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    draw = relationship("DrawResult", back_populates="delivery_events")

class AuditLog(Base):
    """Immutable audit trail recording every significant system change and administrative action."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    entity_name = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=True)
    before_state_json = Column(Text, nullable=True)
    after_state_json = Column(Text, nullable=True)
    campaign_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
