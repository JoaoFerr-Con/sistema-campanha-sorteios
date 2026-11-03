"""Pydantic v2 DTOs for request validation and response serialization."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=3, max_length=128)
    role: str = Field(..., pattern="^(ADMIN|ATENDENTE|PERMISSIONARIO)$")
    permissionario_id: Optional[int] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    permissionario_id: Optional[int] = None
    is_active: bool
    is_demo: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class StagingReviewRequest(BaseModel):
    staging_row_ids: List[int]
    decision: str = Field(..., pattern="^(APROVADO|REJEITADO|CONCILIADO)$")
    justification: str = Field(..., min_length=5)
    confirmed_box_number: Optional[str] = None
    confirmed_permissionario_name: Optional[str] = None
    confirmed_activity: Optional[str] = None
    is_vago: bool = False

class BoxCreateRequest(BaseModel):
    box_number: str
    sector: Optional[str] = None
    official_status: str = Field("CONFIRMADO", pattern="^(CONFIRMADO|VAGO_CONFIRMADO|EM_REGULARIZACAO|SEM_USO)$")
    notes: Optional[str] = None

class PermissionarioCreateRequest(BaseModel):
    name: str = Field(..., min_length=3)
    document_cpf_cnpj: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = Field("ATIVO", pattern="^(ATIVO|SUSPENSO|INATIVO|BLOQUEADO)$")
    sebrae_qualification_level: str = "NIVEL_1_REGULAR"

class BindBoxPermissionarioRequest(BaseModel):
    box_id: int
    permissionario_id: int
    activity_name: str
    authorization_term_ref: Optional[str] = None

class PrizeInput(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    description: Optional[str] = None
    estimated_value: Optional[float] = Field(None, ge=0)
    draw_date: Optional[datetime] = None

class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=160)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    purchase_start_date: datetime
    purchase_end_date: datetime
    registration_end_date: datetime
    min_purchase_value: float = Field(20.0, ge=1.0)
    max_numbers_per_cpf: int = Field(50, ge=1)
    legal_promoter_name: Optional[str] = None
    legal_promoter_doc: Optional[str] = None
    draw_method: str = "LOTERIA_FEDERAL"
    draw_approximation_rule: Optional[str] = Field(None, pattern="^(SOMENTE_EXATO|SUPERIOR_DEPOIS_INFERIOR|MAIS_PROXIMO)$")
    regulation_reference: Optional[str] = Field(None, max_length=160)
    regulation_url: Optional[str] = Field(None, max_length=255)
    regulation_notes: Optional[str] = None
    prizes: Optional[List[PrizeInput]] = None

class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=160)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    purchase_start_date: Optional[datetime] = None
    purchase_end_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None
    min_purchase_value: Optional[float] = Field(None, ge=1.0)
    max_numbers_per_cpf: Optional[int] = Field(None, ge=1)
    legal_promoter_name: Optional[str] = None
    legal_promoter_doc: Optional[str] = None
    draw_approximation_rule: Optional[str] = Field(None, pattern="^(SOMENTE_EXATO|SUPERIOR_DEPOIS_INFERIOR|MAIS_PROXIMO)$")
    regulation_reference: Optional[str] = Field(None, max_length=160)
    regulation_url: Optional[str] = Field(None, max_length=255)
    regulation_notes: Optional[str] = None
    prizes: Optional[List[PrizeInput]] = None

class CampaignLegalApprovalRequest(BaseModel):
    legal_promoter_ok: bool
    participant_compliance_ok: bool
    prizes_funded_ok: bool
    rules_approved_ok: bool
    lgpd_declared_ok: bool
    electoral_cleared_ok: bool
    legal_promoter_name: str
    legal_promoter_doc: str
    justification: str = Field(..., min_length=5)

class CampaignStatusTransitionRequest(BaseModel):
    target_status: str = Field(..., pattern="^(EM_ELABORACAO|AGUARDANDO_APROVACAO|APROVADA|ATIVA|ENCERRADA|CANCELADA)$")
    justification: Optional[str] = None

class VoucherBatchCreateRequest(BaseModel):
    campaign_id: int
    box_id: int
    permissionario_id: int
    code_prefix: str = Field(..., min_length=2, max_length=10)
    start_number: int = Field(..., ge=1)
    end_number: int = Field(..., ge=1)
    notes: Optional[str] = None

class VoucherIssueRequest(BaseModel):
    voucher_code: str
    issued_value: float = Field(..., ge=0.01)
    invoice_doc_number: Optional[str] = None

class VoucherIncidentRequest(BaseModel):
    voucher_code: str
    status: str = Field(..., pattern="^(EXTRAVIADO|DEVOLVIDO|CANCELADO)$")
    reason: str = Field(..., min_length=5)

class ParticipantLookupOrRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=3)
    document_cpf: str = Field(..., min_length=11)
    phone: str = Field(..., min_length=8)
    email: Optional[str] = None
    neighborhood: Optional[str] = None

    @field_validator("document_cpf")
    @classmethod
    def normalize_cpf(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("O CPF deve conter exatamente 11 dígitos numéricos.")
        return digits

class ValidateAndIssueLuckyNumberRequest(BaseModel):
    campaign_id: int
    voucher_code: str
    participant_cpf: str
    participant_name: str
    participant_phone: str
    participant_neighborhood: Optional[str] = None
    participant_email: Optional[str] = None
    consent_lgpd: bool = True

class FederalLotteryDrawRequest(BaseModel):
    campaign_id: int
    contest_number: str = Field(..., max_length=16)
    draw_date: datetime
    extraction_prizes: List[str] = Field(..., min_length=5, max_length=5)
    prize_id: Optional[int] = None
    prize_title: Optional[str] = None

class DrawAnnulRequest(BaseModel):
    reason: str = Field(..., min_length=20)

class FreezeBaseRequest(BaseModel):
    campaign_id: int

class PrizeDeliveryUpdateRequest(BaseModel):
    delivery_status: str = Field(..., pattern="^(PENDENTE|CONTATADO|ENTREGUE|NAO_LOCALIZADO|RECUSADO)$")
    delivery_notes: Optional[str] = None

class BatchCancelRequest(BaseModel):
    reason: str = Field(..., min_length=10)

class PermissionarioUpdateRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    document_cpf_cnpj: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(ATIVO|SUSPENSO|INATIVO|BLOQUEADO)$")
    sebrae_qualification_level: Optional[str] = None
    justification: str = Field(..., min_length=5)

class UserActiveRequest(BaseModel):
    is_active: bool

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
