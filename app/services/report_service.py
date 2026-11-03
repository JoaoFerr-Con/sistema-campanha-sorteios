"""Indicadores gerenciais, auditoria pesquisável e exportações (CSV/Excel)."""
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.entities import (
    Box, Permissionario, Campaign, Voucher, Participation, ValidationAttempt, BoxOccupancy, AuditLog,
    VoucherBatch, Participant, DrawResult,
)
from app.services.audit_service import mask_cpf

ACTION_LABELS = {
    "LOGIN": "Entrada no sistema", "LOGIN_FAILED": "Tentativa de entrada recusada", "LOGOUT": "Saída do sistema",
    "PASSWORD_CHANGED": "Senha alterada", "USER_CREATED": "Usuário criado", "USER_ACTIVATED": "Usuário reativado",
    "USER_DEACTIVATED": "Usuário desativado", "EXCEL_IMPORT_STAGING": "Planilha carregada para conferência",
    "STAGING_REVIEW": "Linha da planilha revisada", "PERMISSIONARIO_UPDATED": "Cadastro de permissionário alterado",
    "CAMPAIGN_CREATED": "Campanha criada", "CAMPAIGN_UPDATED": "Campanha editada",
    "CAMPAIGN_LEGAL_APPROVAL": "Aprovação jurídica registrada", "CAMPAIGN_STATUS_TRANSITION": "Situação da campanha alterada",
    "BATCH_CREATED": "Lote de talões distribuído", "BATCH_CANCELLED": "Lote cancelado",
    "VOUCHER_ISSUED_BY_MERCHANT": "Comprovante emitido pelo box", "VOUCHER_INCIDENT_EXTRAVIADO": "Comprovante extraviado",
    "VOUCHER_INCIDENT_DEVOLVIDO": "Comprovante devolvido", "VOUCHER_INCIDENT_CANCELADO": "Comprovante cancelado",
    "PARTICIPATION_VALIDATED": "Participação validada no balcão", "DRAW_BASE_FROZEN": "Base de participações congelada",
    "DRAW_EXECUTED_LOTERIA_FEDERAL": "Apuração registrada", "DRAW_ANNULLED": "Apuração anulada",
    "PRIZE_DELIVERY_UPDATED": "Entrega de prêmio atualizada",
    "EXPORT_PERSONAL_DATA": "Exportação com dados pessoais",
    "PERMISSIONARIO_CREATED": "Permissionário cadastrado",
    "BOX_HOLDER_ASSIGNED": "Titular vinculado ao box",
    "BOX_HOLDER_TRANSFERRED": "Troca de titular do box",
    "BOX_HOLDER_RELEASED": "Vínculo do box encerrado",
    "BOX_UPDATED": "Box alterado",
}


def _parse_day(value: Optional[str], end: bool = False) -> Optional[datetime]:
    if not value:
        return None
    d = datetime.fromisoformat(value[:10])
    return d + timedelta(days=1) if end else d


def get_dashboard_kpis(db: Session, campaign_id: Optional[int] = None, date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> Dict[str, Any]:
    """Todos os números vêm de consultas ao banco; filtros opcionais por campanha e período."""
    d0, d1 = _parse_day(date_from), _parse_day(date_to, end=True)

    box_counts = dict(db.query(Box.official_status, func.count(Box.id)).group_by(Box.official_status).all())
    perms_active = db.query(Permissionario).filter(Permissionario.status == "ATIVO").count()
    perms_total = db.query(Permissionario).count()
    camp_counts = dict(db.query(Campaign.status, func.count(Campaign.id)).group_by(Campaign.status).all())

    vq = db.query(Voucher.status, func.count(Voucher.id))
    if campaign_id:
        vq = vq.filter(Voucher.campaign_id == campaign_id)
    v = dict(vq.group_by(Voucher.status).all())
    v_incidents = sum(v.get(s, 0) for s in ["EXTRAVIADO", "DEVOLVIDO", "CANCELADO"])
    v_total = sum(v.values())

    pq = db.query(Participation)
    if campaign_id:
        pq = pq.filter(Participation.campaign_id == campaign_id)
    if d0:
        pq = pq.filter(Participation.validated_at >= d0)
    if d1:
        pq = pq.filter(Participation.validated_at < d1)
    total_participations = pq.count()
    unique_participants = pq.with_entities(func.count(func.distinct(Participation.participant_id))).scalar() or 0

    aq = db.query(ValidationAttempt)
    if campaign_id:
        aq = aq.filter(ValidationAttempt.campaign_id == campaign_id)
    if d0:
        aq = aq.filter(ValidationAttempt.created_at >= d0)
    if d1:
        aq = aq.filter(ValidationAttempt.created_at < d1)
    attempts_success = aq.filter(ValidationAttempt.success == True).count()
    attempts_rejected = aq.filter(ValidationAttempt.success == False).count()
    rejections = (aq.filter(ValidationAttempt.success == False)
                  .with_entities(ValidationAttempt.refusal_reason, func.count(ValidationAttempt.id))
                  .group_by(ValidationAttempt.refusal_reason).order_by(func.count(ValidationAttempt.id).desc())
                  .limit(8).all())

    # Atividade comercial vigente do box que originou cada participação
    act_q = (pq.join(BoxOccupancy, (BoxOccupancy.box_id == Participation.box_id) & (BoxOccupancy.is_current == True))
             .with_entities(BoxOccupancy.activity_name, func.count(Participation.id))
             .group_by(BoxOccupancy.activity_name).order_by(func.count(Participation.id).desc()))
    by_activity = [{"activity": a, "participations": n} for a, n in act_q.all()]

    top_q = (pq.join(Permissionario, Permissionario.id == Participation.permissionario_id)
             .join(Box, Box.id == Participation.box_id)
             .with_entities(Permissionario.name, Box.box_number, func.count(Participation.id))
             .group_by(Permissionario.name, Box.box_number).order_by(func.count(Participation.id).desc()).limit(10))
    by_permissionario = [{"permissionario": n, "box": b, "participations": c} for n, b, c in top_q.all()]

    day_q = (pq.with_entities(func.date(Participation.validated_at), func.count(Participation.id))
             .group_by(func.date(Participation.validated_at)).order_by(func.date(Participation.validated_at)))
    by_day = [{"day": str(d), "participations": n} for d, n in day_q.all()][-30:]

    upcoming = []
    now = datetime.utcnow()
    for c in db.query(Campaign).filter(Campaign.status.in_(["ATIVA", "APROVADA"])).all():
        for label, dt in [("Fim das compras", c.purchase_end_date), ("Fim do cadastro de comprovantes", c.registration_end_date),
                          ("Término da campanha", c.end_date)]:
            if dt and dt >= now:
                upcoming.append({"campaign": c.name, "campaign_id": c.id, "event": label, "date": dt.isoformat()})
        for p in c.prizes:
            if p.draw_date and p.draw_date >= now:
                upcoming.append({"campaign": c.name, "campaign_id": c.id, "event": f"Extração — {p.title}",
                                 "date": p.draw_date.isoformat()})
    upcoming.sort(key=lambda x: x["date"])

    distributed_total = v.get("DISTRIBUIDO", 0) + v.get("EMITIDO", 0) + v.get("UTILIZADO", 0)
    return {
        "filters": {"campaign_id": campaign_id, "date_from": date_from, "date_to": date_to},
        "boxes": {
            "total_capacity_map": 368,
            "total_cataloged": sum(box_counts.values()),
            "confirmed_active": box_counts.get("CONFIRMADO", 0),
            "confirmed_vacant": box_counts.get("VAGO_CONFIRMADO", 0),
            "under_regularization": box_counts.get("EM_REGULARIZACAO", 0),
            "out_of_use": box_counts.get("SEM_USO", 0),
        },
        "permissionarios": {"total": perms_total, "active": perms_active},
        "campaigns": {
            "total": sum(camp_counts.values()),
            "active": camp_counts.get("ATIVA", 0),
            "draft": camp_counts.get("EM_ELABORACAO", 0),
            "awaiting_approval": camp_counts.get("AGUARDANDO_APROVACAO", 0),
            "approved": camp_counts.get("APROVADA", 0),
            "closed": camp_counts.get("ENCERRADA", 0),
        },
        "vouchers": {
            "total": v_total,
            "distributed": v.get("DISTRIBUIDO", 0),
            "issued": v.get("EMITIDO", 0),
            "used_validated": v.get("UTILIZADO", 0),
            "available": v.get("DISTRIBUIDO", 0) + v.get("EMITIDO", 0),
            "incidents": v_incidents,
            "conversion_pct": round(100 * v.get("UTILIZADO", 0) / distributed_total, 1) if distributed_total else None,
        },
        "participations": {
            "total_validated": total_participations,
            "unique_consumers": unique_participants,
            "by_activity": by_activity,
            "by_permissionario": by_permissionario,
            "by_day": by_day,
        },
        "validation_attempts": {
            "successful": attempts_success,
            "rejected": attempts_rejected,
            "rejections_breakdown": [{"reason": r or "Não especificado", "count": n} for r, n in rejections],
        },
        "upcoming": upcoming[:8],
    }


def _audit_query(db: Session, filters: Dict[str, Any]):
    q = db.query(AuditLog)
    if filters.get("username"):
        q = q.filter(AuditLog.username.ilike(f"%{filters['username']}%"))
    if filters.get("action"):
        q = q.filter(AuditLog.action == filters["action"])
    if filters.get("entity"):
        q = q.filter(AuditLog.entity_name == filters["entity"])
    if filters.get("campaign_id"):
        q = q.filter(AuditLog.campaign_id == filters["campaign_id"])
    if filters.get("date_from"):
        q = q.filter(AuditLog.created_at >= _parse_day(filters["date_from"]))
    if filters.get("date_to"):
        q = q.filter(AuditLog.created_at < _parse_day(filters["date_to"], end=True))
    if filters.get("q"):
        like = f"%{filters['q']}%"
        q = q.filter(AuditLog.after_state_json.ilike(like) | AuditLog.before_state_json.ilike(like)
                     | AuditLog.entity_id.ilike(like))
    return q


def _serialize_log(l: AuditLog) -> Dict[str, Any]:
    return {
        "id": l.id,
        "username": l.username or "SISTEMA",
        "action": l.action,
        "action_label": ACTION_LABELS.get(l.action, l.action),
        "entity": l.entity_name,
        "entity_id": l.entity_id,
        "campaign_id": l.campaign_id,
        "before": l.before_state_json,
        "after": l.after_state_json,
        "ip": l.ip_address,
        "timestamp": l.created_at.isoformat(),
    }


def get_audit_trail(db: Session, limit: int = 50, offset: int = 0, **filters) -> Any:
    q = _audit_query(db, filters)
    if not filters.get("paged"):
        return [_serialize_log(l) for l in q.order_by(AuditLog.id.desc()).limit(limit).all()]
    total = q.count()
    items = [_serialize_log(l) for l in q.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()]
    return {"total": total, "items": items, "actions": ACTION_LABELS}


# ---------------------------------------------------------------- exportações

def dataset(db: Session, name: str, campaign_id: Optional[int] = None, audit_filters: Optional[Dict] = None,
            full_cpf: bool = False):
    """Retorna (título, cabeçalhos, linhas) para cada relatório."""
    if name == "participacoes":
        q = db.query(Participation)
        if campaign_id:
            q = q.filter(Participation.campaign_id == campaign_id)
        rows = []
        for p in q.order_by(Participation.campaign_id, Participation.lucky_number).all():
            rows.append([p.campaign.name, p.lucky_number, p.voucher.full_code,
                         p.voucher.box.box_number if p.voucher.box else "",
                         p.voucher.permissionario.name if p.voucher.permissionario else "",
                         p.participant.document_cpf if full_cpf else mask_cpf(p.participant.document_cpf),
                         p.participant.full_name, p.participant.neighborhood or "",
                         p.attendant.full_name if p.attendant else "", p.validated_at.strftime("%d/%m/%Y %H:%M")])
        return ("Participações validadas",
                ["Campanha", "Número da sorte", "Comprovante", "Box", "Permissionário", "CPF", "Participante",
                 "Bairro", "Atendente", "Validado em (UTC)"], rows)
    if name == "lotes":
        from app.services.voucher_service import list_batches
        rows = [[b["campaign_name"], b["batch_number"], b["box_number"], b["permissionario_name"],
                 f"{b['first_code']} a {b['last_code']}", b["total"], b["issued"], b["used"], b["available"],
                 b["incidents"], b["status"], b["distributed_by"], (b["distributed_at"] or "")[:16].replace("T", " ")]
                for b in list_batches(db, campaign_id=campaign_id)]
        return ("Distribuição de talões e prestação de contas",
                ["Campanha", "Lote", "Box", "Permissionário", "Intervalo", "Total", "Emitidos", "Utilizados",
                 "Disponíveis", "Ocorrências", "Situação", "Responsável", "Distribuído em (UTC)"], rows)
    if name == "permissionarios":
        rows = []
        for p in db.query(Permissionario).order_by(Permissionario.name).all():
            boxes = ", ".join(o.box.box_number for o in p.occupancies if o.is_current and o.box)
            acts = ", ".join(sorted({o.activity_name for o in p.occupancies if o.is_current}))
            vq = db.query(Voucher.status, func.count(Voucher.id)).filter(Voucher.permissionario_id == p.id)
            if campaign_id:
                vq = vq.filter(Voucher.campaign_id == campaign_id)
            vc = dict(vq.group_by(Voucher.status).all())
            rows.append([p.name, boxes, acts, p.status, sum(vc.values()), vc.get("UTILIZADO", 0),
                         vc.get("DISTRIBUIDO", 0) + vc.get("EMITIDO", 0)])
        return ("Permissionários", ["Nome", "Boxes", "Atividade", "Situação", "Comprovantes recebidos",
                                    "Utilizados", "Disponíveis"], rows)
    if name == "ocorrencias":
        q = db.query(ValidationAttempt).filter(ValidationAttempt.success == False)
        if campaign_id:
            q = q.filter(ValidationAttempt.campaign_id == campaign_id)
        rows = [[a.created_at.strftime("%d/%m/%Y %H:%M"), a.voucher_code, mask_cpf(a.participant_cpf),
                 a.refusal_reason or ""] for a in q.order_by(ValidationAttempt.id.desc()).all()]
        return ("Recusas no balcão", ["Data (UTC)", "Comprovante", "CPF", "Motivo"], rows)
    if name == "auditoria":
        q = _audit_query(db, audit_filters or {})
        rows = [[l.created_at.strftime("%d/%m/%Y %H:%M:%S"), l.username or "SISTEMA",
                 ACTION_LABELS.get(l.action, l.action), l.entity_name, l.entity_id or "",
                 l.before_state_json or "", l.after_state_json or ""] for l in q.order_by(AuditLog.id.desc()).limit(20000).all()]
        return ("Histórico de auditoria", ["Data (UTC)", "Usuário", "Operação", "Entidade", "Registro",
                                           "Antes", "Depois"], rows)
    raise ValueError("Relatório desconhecido")


def to_csv(headers: List[str], rows: List[List[Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(headers)
    w.writerows(rows)
    return "﻿" + buf.getvalue()  # BOM para o Excel abrir acentos corretamente


def to_xlsx(title: str, headers: List[str], rows: List[List[Any]], filters_text: str, issued_by: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(["Prefeitura Municipal de Barcarena — SEICOMTEC · Complexo Comercial de Barcarena"])
    ws.append([title])
    ws.append([f"Filtros: {filters_text}"])
    ws.append([f"Emitido em {datetime.utcnow():%d/%m/%Y %H:%M} UTC por {issued_by}"])
    ws.append([])
    ws["A2"].font = Font(bold=True, size=14)
    ws.append(headers)
    hdr_row = ws.max_row
    for cell in ws[hdr_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0F5E57")
        cell.alignment = Alignment(vertical="center")
    for r in rows:
        ws.append(r)
    for i, h in enumerate(headers, start=1):
        width = max([len(str(h))] + [len(str(r[i - 1])) for r in rows[:500]]) + 2
        ws.column_dimensions[get_column_letter(i)].width = min(width, 60)
    ws.freeze_panes = ws.cell(row=hdr_row + 1, column=1)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
