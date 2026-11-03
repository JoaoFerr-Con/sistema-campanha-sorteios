"""API REST /api/v1. Toda rota de dados exige autenticação; o perfil vem do usuário no banco."""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response, HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, get_current_user_payload, require_roles
from app.models.entities import (
    User, Box, Permissionario, Campaign, ImportStagingRow, Participation, ValidationAttempt, DrawResult,
    BoxOccupancy, VoucherBatch, Voucher,
)
from app.schemas.dto import (
    UserLoginRequest, TokenResponse, UserResponse, UserCreateRequest, UserActiveRequest, PasswordChangeRequest,
    StagingReviewRequest, PermissionarioUpdateRequest, CampaignCreateRequest, CampaignUpdateRequest,
    CampaignLegalApprovalRequest, CampaignStatusTransitionRequest, VoucherBatchCreateRequest, BatchCancelRequest,
    ValidateAndIssueLuckyNumberRequest, VoucherIssueRequest, VoucherIncidentRequest, FederalLotteryDrawRequest,
    FreezeBaseRequest, DrawAnnulRequest, PrizeDeliveryUpdateRequest,
    PermissionarioCreateFullRequest, BoxAssignRequest, BoxReleaseRequest, BoxUpdateRequest,
)
from app.services import (
    auth_service, box_service, campaign_service, voucher_service, attendance_service, portal_service,
    report_service, draw_service,
)
from app.services.audit_service import mask_cpf

api_router = APIRouter(prefix="/api/v1")
ADMIN = require_roles(["ADMIN"])
STAFF = require_roles(["ADMIN", "ATENDENTE"])
ANY = get_current_user_payload


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "")[:64]


# ================= SISTEMA =================

@api_router.get("/system/info")
def system_info(db: Session = Depends(get_db)):
    """Informações públicas para a tela de entrada (sem dados pessoais)."""
    from app.core.seed import DEMO_ACCOUNTS, DEMO_PASSWORD
    info = {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "demo_mode": settings.demo_mode,
        "ephemeral_database": settings.is_ephemeral_db,
        "setup_required": not db.query(User).filter(User.role == "ADMIN").first(),
    }
    if settings.demo_mode:
        info["demo_accounts"] = [{**a, "password": DEMO_PASSWORD} for a in DEMO_ACCOUNTS]
    return info


# ================= AUTENTICAÇÃO =================

@api_router.post("/auth/login", response_model=TokenResponse)
def login(body: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, body.username, body.password, ip=client_ip(request))
    token = create_access_token(user.id, user.username, user.role, user.permissionario_id, user.token_version or 0)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@api_router.get("/auth/me", response_model=UserResponse)
def get_current_user(payload: dict = Depends(ANY), db: Session = Depends(get_db)):
    return UserResponse.model_validate(db.query(User).filter(User.id == payload["user_id"]).first())


@api_router.post("/auth/logout")
def logout(payload: dict = Depends(ANY), db: Session = Depends(get_db)):
    auth_service.logout_user(db, payload["user_id"])
    return {"status": "success"}


@api_router.post("/auth/password")
def change_password(body: PasswordChangeRequest, payload: dict = Depends(ANY), db: Session = Depends(get_db)):
    auth_service.change_password(db, payload["user_id"], body.current_password, body.new_password)
    return {"status": "success", "message": "Senha alterada. Entre novamente com a nova senha."}


# ================= USUÁRIOS =================

@api_router.get("/users")
def list_users(payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return [UserResponse.model_validate(u).model_dump(mode="json") | {
        "permissionario_name": u.permissionario.name if u.permissionario else None}
        for u in db.query(User).order_by(User.role, User.username).all()]


@api_router.post("/users")
def create_user(body: UserCreateRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    u = auth_service.create_user(db, body.username, body.password, body.full_name, body.role, body.permissionario_id,
                                 payload["user_id"], payload["username"])
    return {"status": "success", "user_id": u.id}


@api_router.post("/users/{user_id}/active")
def set_user_active(user_id: int, body: UserActiveRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    u = auth_service.set_user_active(db, user_id, body.is_active, payload["user_id"], payload["username"])
    return {"status": "success", "is_active": u.is_active}


# ================= BOXES, CONFERÊNCIA E PERMISSIONÁRIOS =================

@api_router.post("/boxes/import-staging")
def import_excel_to_staging(payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    target_path = settings.data_dir / settings.excel_filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Planilha oficial não encontrada na pasta data/.")
    return box_service.import_spreadsheet_to_staging(db, target_path, user_id=payload["user_id"],
                                                     username=payload["username"])


@api_router.get("/boxes/staging")
def list_staging_rows(status_filter: Optional[str] = None, only_flagged: bool = False, q: Optional[str] = None,
                      limit: int = 100, offset: int = 0, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    query = db.query(ImportStagingRow)
    if status_filter:
        query = query.filter(ImportStagingRow.status == status_filter)
    if only_flagged:
        query = query.filter(ImportStagingRow.discrepancy_flags != "[]")
    if q:
        like = f"%{q}%"
        query = query.filter(ImportStagingRow.raw_box_number.ilike(like) | ImportStagingRow.raw_permissionario_name.ilike(like))
    total = query.count()
    rows = query.order_by(ImportStagingRow.row_number.asc()).offset(offset).limit(min(limit, 500)).all()
    return {
        "total": total,
        "pending_total": db.query(ImportStagingRow).filter(ImportStagingRow.status == "PENDENTE_REVISAO").count(),
        "rows": [{
            "id": r.id, "row_number": r.row_number, "box_number": r.raw_box_number,
            "permissionario_name": r.raw_permissionario_name, "activity": r.raw_activity, "status": r.status,
            "discrepancy_flags": r.discrepancy_flags, "admin_decision": r.admin_decision,
            "admin_justification": r.admin_justification,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        } for r in rows],
    }


@api_router.post("/boxes/staging/review")
def review_staging_row(body: StagingReviewRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    has_overrides = any([body.confirmed_box_number, body.confirmed_permissionario_name, body.confirmed_activity])
    if has_overrides and len(body.staging_row_ids) > 1:
        raise HTTPException(status_code=400, detail="Correções de box, nome ou atividade só podem ser aplicadas a uma linha por vez.")
    reviewed = []
    for sid in body.staging_row_ids:
        item = box_service.review_staging_row(
            db=db, staging_id=sid, decision=body.decision, justification=body.justification,
            user_id=payload["user_id"], username=payload["username"],
            confirmed_box_number=body.confirmed_box_number,
            confirmed_permissionario_name=body.confirmed_permissionario_name,
            confirmed_activity=body.confirmed_activity, is_vago=body.is_vago)
        reviewed.append(item.id)
    return {"status": "success", "reviewed_count": len(reviewed), "ids": reviewed}


@api_router.get("/boxes/summary")
def get_boxes_summary(payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    return box_service.get_boxes_summary(db)


@api_router.get("/boxes/map")
def get_box_map(payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    return box_service.get_box_map(db)


@api_router.get("/activities")
def list_activities(payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    return box_service.list_activities(db)


@api_router.get("/boxes/{box_number}/detail")
def get_box_detail(box_number: str, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return box_service.box_detail(db, box_number)


@api_router.patch("/boxes/{box_number}")
def update_box(box_number: str, body: BoxUpdateRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    b = box_service.update_box(db, box_number, body.model_dump(), payload["user_id"], payload["username"])
    return {"status": "success", "box_number": b.box_number, "official_status": b.official_status}


@api_router.post("/boxes/{box_number}/holder")
def assign_box_holder(box_number: str, body: BoxAssignRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    occ = box_service.assign_box(db, box_number, body.permissionario_id, body.activity_name, body.authorization_term_ref,
                                 body.justification, payload["user_id"], payload["username"],
                                 acknowledge_outstanding=body.acknowledge_outstanding)
    return {"status": "success", "box_number": box_number, "permissionario_id": occ.permissionario_id}


@api_router.post("/boxes/{box_number}/release")
def release_box_holder(box_number: str, body: BoxReleaseRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    b = box_service.release_box(db, box_number, body.target_status, body.justification, payload["user_id"],
                                payload["username"], acknowledge_outstanding=body.acknowledge_outstanding)
    return {"status": "success", "box_number": b.box_number, "official_status": b.official_status}


@api_router.get("/boxes")
def list_boxes(status: Optional[str] = None, payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    query = db.query(Box)
    if status:
        query = query.filter(Box.official_status == status)
    res = []
    for b in sorted(query.all(), key=lambda b: int(b.box_number) if b.box_number.isdigit() else 9999):
        occ = next((o for o in b.occupancies if o.is_current), None)
        res.append({
            "id": b.id, "box_number": b.box_number, "sector": b.sector, "official_status": b.official_status,
            "permissionario": occ.permissionario.name if occ else None,
            "permissionario_id": occ.permissionario_id if occ else None,
            "permissionario_status": occ.permissionario.status if occ else None,
            "activity": occ.activity_name if occ else None,
        })
    return res


@api_router.get("/permissionarios")
def list_permissionarios(q: Optional[str] = None, status: Optional[str] = None, activity: Optional[str] = None,
                         payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    query = db.query(Permissionario)
    if q:
        query = query.filter(Permissionario.name.ilike(f"%{q}%"))
    if status:
        query = query.filter(Permissionario.status == status)
    out = []
    for p in query.order_by(Permissionario.name.asc()).all():
        current = [o for o in p.occupancies if o.is_current]
        acts = sorted({o.activity_name for o in current})
        if activity and activity not in acts:
            continue
        out.append({"id": p.id, "name": p.name, "status": p.status, "sebrae_level": p.sebrae_qualification_level,
                    "boxes": [o.box.box_number for o in current if o.box], "activities": acts,
                    "has_portal_user": bool(p.user)})
    if q and q.strip().isdigit():  # busca por número de box
        by_box = db.query(BoxOccupancy).join(Box).filter(Box.box_number == q.strip(), BoxOccupancy.is_current == True).all()
        ids = {o["id"] for o in out}
        for o in by_box:
            p = o.permissionario
            if p.id not in ids:
                out.append({"id": p.id, "name": p.name, "status": p.status, "sebrae_level": p.sebrae_qualification_level,
                            "boxes": [x.box.box_number for x in p.occupancies if x.is_current],
                            "activities": sorted({x.activity_name for x in p.occupancies if x.is_current}),
                            "has_portal_user": bool(p.user)})
    return out


@api_router.post("/permissionarios")
def create_permissionario(body: PermissionarioCreateFullRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    p = box_service.create_permissionario(db, body.model_dump(), payload["user_id"], payload["username"])
    return {"status": "success", "id": p.id, "name": p.name}


@api_router.get("/permissionarios/{perm_id}")
def get_permissionario(perm_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    p = db.query(Permissionario).filter(Permissionario.id == perm_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Permissionário não encontrado.")
    from app.models.entities import AuditLog
    history = db.query(AuditLog).filter(AuditLog.entity_name == "Permissionario", AuditLog.entity_id == str(p.id)) \
        .order_by(AuditLog.id.desc()).all()
    return {
        "id": p.id, "name": p.name, "status": p.status, "document": p.document_cpf_cnpj, "phone": p.phone,
        "email": p.email, "sebrae_level": p.sebrae_qualification_level, "created_at": p.created_at.isoformat(),
        "portal_user": p.user.username if p.user else None,
        "occupancies": [{"box_number": o.box.box_number, "activity": o.activity_name, "is_current": o.is_current,
                         "start_date": o.start_date.isoformat(), "end_date": o.end_date.isoformat() if o.end_date else None,
                         "term": o.authorization_term_ref} for o in sorted(p.occupancies, key=lambda o: o.start_date, reverse=True)],
        "batches": voucher_service.list_batches(db, permissionario_id=p.id),
        "participations": db.query(Participation).filter(Participation.permissionario_id == p.id).count(),
        "history": [{"timestamp": h.created_at.isoformat(), "username": h.username, "action": h.action,
                     "before": h.before_state_json, "after": h.after_state_json} for h in history],
    }


@api_router.patch("/permissionarios/{perm_id}")
def update_permissionario(perm_id: int, body: PermissionarioUpdateRequest, payload: dict = Depends(ADMIN),
                          db: Session = Depends(get_db)):
    p = box_service.update_permissionario(db, perm_id, body.model_dump(), payload["user_id"], payload["username"])
    return {"status": "success", "id": p.id, "new_status": p.status}


# ================= CAMPANHAS =================

@api_router.get("/campaigns")
def list_campaigns(payload: dict = Depends(ANY), db: Session = Depends(get_db)):
    query = db.query(Campaign)
    if payload["role"] != "ADMIN":
        query = query.filter(Campaign.status.in_(["ATIVA", "ENCERRADA"]))
    return [campaign_service.serialize_campaign(c) for c in query.order_by(Campaign.id.desc()).all()]


@api_router.get("/campaigns/options")
def campaign_options():
    return {"approximation_rules": campaign_service.APPROXIMATION_RULES,
            "legal_labels": campaign_service.LEGAL_LABELS, "status_labels": campaign_service.STATUS_LABELS}


@api_router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    c = campaign_service.get_campaign_or_404(db, campaign_id)
    data = campaign_service.serialize_campaign(c)
    data["indicators"] = report_service.get_dashboard_kpis(db, campaign_id=campaign_id)
    return data


@api_router.post("/campaigns")
def create_campaign(body: CampaignCreateRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    camp = campaign_service.create_campaign(db, body.model_dump(), payload["user_id"], payload["username"])
    return {"status": "success", "campaign_id": camp.id, "campaign_status": camp.status}


@api_router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, body: CampaignUpdateRequest, payload: dict = Depends(ADMIN),
                    db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    camp = campaign_service.update_campaign(db, campaign_id, data, payload["user_id"], payload["username"])
    return {"status": "success", "campaign": campaign_service.serialize_campaign(camp)}


@api_router.post("/campaigns/{campaign_id}/legal-approvals")
def register_legal_approvals(campaign_id: int, body: CampaignLegalApprovalRequest, payload: dict = Depends(ADMIN),
                             db: Session = Depends(get_db)):
    camp = campaign_service.register_legal_approvals(db, campaign_id, body.model_dump(), payload["user_id"], payload["username"])
    return {"status": "success", "campaign_id": camp.id, "campaign_status": camp.status}


@api_router.post("/campaigns/{campaign_id}/transition")
def transition_campaign(campaign_id: int, body: CampaignStatusTransitionRequest, payload: dict = Depends(ADMIN),
                        db: Session = Depends(get_db)):
    camp = campaign_service.transition_campaign_status(db, campaign_id, body.target_status, payload["user_id"],
                                                       payload["username"], body.justification)
    return {"status": "success", "campaign_id": camp.id, "new_status": camp.status}


# ================= TALÕES E COMPROVANTES =================

@api_router.post("/vouchers/batches")
def create_voucher_batch(body: VoucherBatchCreateRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    batch = voucher_service.create_voucher_batch(db, body.campaign_id, body.box_id, body.permissionario_id,
                                                 body.code_prefix, body.start_number, body.end_number,
                                                 payload["user_id"], payload["username"], body.notes)
    return {"status": "success", "batch_id": batch.id, "batch_number": batch.batch_number,
            "total_vouchers": batch.total_vouchers}


@api_router.get("/vouchers/batches")
def list_voucher_batches(campaign_id: Optional[int] = None, q: Optional[str] = None, payload: dict = Depends(ADMIN),
                         db: Session = Depends(get_db)):
    return voucher_service.list_batches(db, campaign_id=campaign_id, q=q)


@api_router.get("/vouchers/batches/next-range")
def next_range(prefix: str, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    """Sugere o próximo número livre para o prefixo informado (evita conflito de intervalo)."""
    from sqlalchemy import func as f
    last = db.query(f.max(VoucherBatch.end_number)).filter(VoucherBatch.code_prefix == prefix.strip().upper()).scalar()
    return {"prefix": prefix.strip().upper(), "next_start": (last or 0) + 1}


@api_router.get("/vouchers/batches/{batch_id}/history")
def get_batch_history(batch_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return voucher_service.batch_history(db, batch_id)


@api_router.get("/vouchers/batches/{batch_id}/vouchers")
def get_batch_vouchers(batch_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    vs = db.query(Voucher).filter(Voucher.batch_id == batch_id).order_by(Voucher.sequence_number).all()
    return [{"code": v.full_code, "status": v.status,
             "lucky_number": v.participation.lucky_number if v.participation else None} for v in vs]


@api_router.post("/vouchers/batches/{batch_id}/cancel")
def cancel_voucher_batch(batch_id: int, body: BatchCancelRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return voucher_service.cancel_batch(db, batch_id, body.reason, payload["user_id"], payload["username"])


@api_router.get("/vouchers/lookup/{code}")
def lookup_voucher(code: str, payload: dict = Depends(ANY), db: Session = Depends(get_db)):
    v_data = voucher_service.query_voucher_by_code(db, code)
    if not v_data:
        raise HTTPException(status_code=404, detail="Comprovante não encontrado.")
    if payload["role"] == "PERMISSIONARIO" and v_data["permissionario_id"] != payload.get("permissionario_id"):
        raise HTTPException(status_code=404, detail="Comprovante não encontrado.")
    return v_data


@api_router.get("/vouchers/eligibility")
def voucher_eligibility(campaign_id: int, code: str, payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    return voucher_service.eligibility(db, campaign_id, code)


@api_router.get("/vouchers/{code}/qr.svg")
def voucher_qr(code: str, payload: dict = Depends(ANY), db: Session = Depends(get_db)):
    v = voucher_service.query_voucher_by_code(db, code)
    if not v or (payload["role"] == "PERMISSIONARIO" and v["permissionario_id"] != payload.get("permissionario_id")):
        raise HTTPException(status_code=404, detail="Comprovante não encontrado.")
    import io
    import segno
    buf = io.BytesIO()
    segno.make(v["full_code"], error="m").save(buf, kind="svg", scale=6, border=2, dark="#12324a")
    return Response(content=buf.getvalue(), media_type="image/svg+xml")


# ================= BALCÃO =================

@api_router.post("/attendance/validate")
def validate_voucher_at_counter(body: ValidateAndIssueLuckyNumberRequest, request: Request,
                                payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    return attendance_service.validate_and_issue_participation(
        db=db, campaign_id=body.campaign_id, voucher_code=body.voucher_code, participant_cpf=body.participant_cpf,
        participant_name=body.participant_name, participant_phone=body.participant_phone,
        participant_neighborhood=body.participant_neighborhood, participant_email=body.participant_email,
        consent_lgpd=body.consent_lgpd, attendant_user_id=payload["user_id"],
        attendant_username=payload["username"], ip_address=client_ip(request))


@api_router.get("/attendance/participant")
def find_participant(cpf: str, campaign_id: Optional[int] = None, payload: dict = Depends(STAFF),
                     db: Session = Depends(get_db)):
    return {"found": False} if not (p := attendance_service.find_participant(db, cpf, campaign_id)) else {"found": True, **p}


@api_router.get("/attendance/attempts")
def list_recent_validation_attempts(limit: int = 50, campaign_id: Optional[int] = None, mine: bool = False,
                                    payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    q = db.query(ValidationAttempt)
    if campaign_id:
        q = q.filter(ValidationAttempt.campaign_id == campaign_id)
    if mine:
        q = q.filter(ValidationAttempt.tried_by_user_id == payload["user_id"])
    attempts = q.order_by(ValidationAttempt.id.desc()).limit(min(limit, 200)).all()
    codes = [a.voucher_code for a in attempts if a.success]
    lucky = {}
    if codes:
        for p in db.query(Participation).join(Voucher).filter(Voucher.full_code.in_(codes)).all():
            lucky[p.voucher.full_code] = p.lucky_number
    return [{"id": a.id, "campaign_id": a.campaign_id, "voucher_code": a.voucher_code,
             "participant_cpf": mask_cpf(a.participant_cpf), "success": a.success,
             "lucky_number": lucky.get(a.voucher_code) if a.success else None,
             "refusal_reason": a.refusal_reason, "timestamp": a.created_at.isoformat()} for a in attempts]


# ================= PORTAL DO PERMISSIONÁRIO =================

def _portal_perm_id(payload: dict, requested: Optional[int], db: Session) -> int:
    """Permissionário: sempre o próprio vínculo (ignora qualquer id enviado). Admin: precisa indicar qual."""
    if payload["role"] == "PERMISSIONARIO":
        if not payload.get("permissionario_id"):
            raise HTTPException(status_code=403, detail="Usuário sem permissionário vinculado.")
        return payload["permissionario_id"]
    if requested:
        return requested
    first = db.query(Permissionario).join(BoxOccupancy).filter(BoxOccupancy.is_current == True).order_by(Permissionario.id).first()
    if not first:
        raise HTTPException(status_code=404, detail="Nenhum permissionário com box vinculado.")
    return first.id


@api_router.get("/portal/overview")
def get_my_portal(permissionario_id: Optional[int] = None, payload: dict = Depends(require_roles(["ADMIN", "PERMISSIONARIO"])),
                  db: Session = Depends(get_db)):
    return portal_service.get_portal_overview(db, _portal_perm_id(payload, permissionario_id, db))


def _owner_for_admin(payload, code, db):
    if payload["role"] == "PERMISSIONARIO":
        return _portal_perm_id(payload, None, db)
    v = db.query(Voucher).filter(Voucher.full_code == voucher_service.normalize_code(code)).first()
    if not v:
        raise HTTPException(status_code=404, detail="Comprovante não encontrado.")
    return v.permissionario_id


@api_router.post("/portal/issue-voucher")
def issue_voucher(body: VoucherIssueRequest, payload: dict = Depends(require_roles(["ADMIN", "PERMISSIONARIO"])),
                  db: Session = Depends(get_db)):
    return portal_service.issue_voucher_by_permissionario(
        db=db, permissionario_id=_owner_for_admin(payload, body.voucher_code, db),
        voucher_code=voucher_service.normalize_code(body.voucher_code), issued_value=body.issued_value,
        user_id=payload["user_id"], username=payload["username"], invoice_doc_number=body.invoice_doc_number)


@api_router.post("/portal/report-incident")
def report_voucher_incident(body: VoucherIncidentRequest, payload: dict = Depends(require_roles(["ADMIN", "PERMISSIONARIO"])),
                            db: Session = Depends(get_db)):
    return portal_service.report_voucher_incident(
        db=db, permissionario_id=_owner_for_admin(payload, body.voucher_code, db),
        voucher_code=voucher_service.normalize_code(body.voucher_code), target_status=body.status,
        reason=body.reason, user_id=payload["user_id"], username=payload["username"])


# ================= INDICADORES, AUDITORIA E RELATÓRIOS =================

@api_router.get("/reports/kpis")
def get_kpis(campaign_id: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
             payload: dict = Depends(STAFF), db: Session = Depends(get_db)):
    return report_service.get_dashboard_kpis(db, campaign_id, date_from, date_to)


@api_router.get("/reports/audit-trail")
def get_audit_trail(limit: int = 50, offset: int = 0, username: Optional[str] = None, action: Optional[str] = None,
                    entity: Optional[str] = None, campaign_id: Optional[int] = None, date_from: Optional[str] = None,
                    date_to: Optional[str] = None, q: Optional[str] = None, paged: bool = False,
                    payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return report_service.get_audit_trail(db, min(limit, 500), offset, username=username, action=action, entity=entity,
                                          campaign_id=campaign_id, date_from=date_from, date_to=date_to, q=q, paged=paged)


@api_router.get("/reports/export/participations.csv")
def export_participations_csv(campaign_id: Optional[int] = None, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    """Mantido por compatibilidade: CSV com CPF completo para uso oficial do promotor."""
    q = db.query(Participation)
    if campaign_id:
        q = q.filter(Participation.campaign_id == campaign_id)
    lines = ["numero_da_sorte,comprovante,box,permissionario,cpf_participante,nome_participante,data_validacao"]
    for p in q.order_by(Participation.lucky_number.asc()).all():
        box_num = p.voucher.box.box_number if p.voucher.box else ""
        perm_name = (p.voucher.permissionario.name if p.voucher.permissionario else "").replace(",", " ")
        lines.append(f"{p.lucky_number},{p.voucher.full_code},{box_num},{perm_name},{p.participant.document_cpf},"
                     f"{p.participant.full_name.replace(',', ' ')},{p.validated_at.isoformat()}")
    from app.services.audit_service import log_audit
    log_audit(db, "EXPORT_PERSONAL_DATA", "Participation", user_id=payload["user_id"], username=payload["username"],
              campaign_id=campaign_id, after_state={"format": "csv", "rows": len(lines) - 1})
    db.commit()
    return PlainTextResponse(content="\n".join(lines), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=participacoes_validadas.csv"})


@api_router.get("/reports/export/{name}.{fmt}")
def export_report(name: str, fmt: str, campaign_id: Optional[int] = None, username: Optional[str] = None,
                  action: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
                  payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="Formato deve ser csv ou xlsx.")
    try:
        title, headers, rows = report_service.dataset(
            db, name, campaign_id, audit_filters={"username": username, "action": action, "campaign_id": campaign_id,
                                                  "date_from": date_from, "date_to": date_to})
    except ValueError:
        raise HTTPException(status_code=404, detail="Relatório desconhecido.")
    camp = db.query(Campaign).filter(Campaign.id == campaign_id).first() if campaign_id else None
    filters_text = ", ".join(x for x in [f"campanha {camp.name}" if camp else "todas as campanhas",
                                         f"de {date_from}" if date_from else "", f"até {date_to}" if date_to else "",
                                         f"usuário {username}" if username else "", f"operação {action}" if action else ""] if x)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    filename = f"{name}_{stamp}.{fmt}"
    if fmt == "csv":
        content, media = report_service.to_csv(headers, rows).encode("utf-8"), "text/csv; charset=utf-8"
    else:
        content = report_service.to_xlsx(title, headers, rows, filters_text, payload["username"])
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(content=content, media_type=media, headers={"Content-Disposition": f"attachment; filename={filename}"})


# ================= APURAÇÃO =================

@api_router.get("/draw/overview/{campaign_id}")
def draw_overview(campaign_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return draw_service.draw_overview(db, campaign_id)


@api_router.post("/draw/freeze")
def freeze_base(body: FreezeBaseRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    snap = draw_service.freeze_base(db, body.campaign_id, payload["user_id"], payload["username"])
    return {"status": "success", "sha256": snap.sha256, "participations_count": snap.participations_count}


@api_router.get("/draw/base/{campaign_id}.csv")
def download_base(campaign_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    content = draw_service.canonical_base_csv(db, campaign_id)
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=base_campanha_{campaign_id}.csv"})


@api_router.post("/draw/execute-federal")
def execute_federal_draw(body: FederalLotteryDrawRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return draw_service.execute_federal_lottery_draw(db, body.campaign_id, body.contest_number, body.draw_date,
                                                     body.extraction_prizes, body.prize_title, payload["user_id"],
                                                     payload["username"], prize_id=body.prize_id)


@api_router.get("/draw/results/{campaign_id}")
def get_draw_results(campaign_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    results = db.query(DrawResult).filter(DrawResult.campaign_id == campaign_id).order_by(DrawResult.id).all()
    return [draw_service.serialize_result(r) for r in results]


@api_router.post("/draw/{draw_id}/annul")
def annul_draw(draw_id: int, body: DrawAnnulRequest, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    d = draw_service.annul_draw(db, draw_id, body.reason, payload["user_id"], payload["username"])
    return {"status": "success", "draw_id": d.id, "draw_status": d.status}


@api_router.post("/draw/{draw_id}/delivery")
def update_prize_delivery(draw_id: int, body: PrizeDeliveryUpdateRequest, payload: dict = Depends(ADMIN),
                          db: Session = Depends(get_db)):
    d = draw_service.update_delivery(db, draw_id, body.delivery_status, body.delivery_notes, payload["user_id"],
                                     payload["username"])
    return {"status": "success", "draw_id": d.id, "delivery_status": d.delivery_status}


@api_router.get("/draw/minutes/{campaign_id}", response_class=HTMLResponse)
def draw_minutes(campaign_id: int, payload: dict = Depends(ADMIN), db: Session = Depends(get_db)):
    return HTMLResponse(draw_service.render_minutes_html(db, campaign_id, payload["username"]))
