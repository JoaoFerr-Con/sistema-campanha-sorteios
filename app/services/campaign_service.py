"""Ciclo de vida da campanha: elaboração em etapas, aprovação jurídica, ativação e encerramento."""
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.entities import Campaign, CampaignPrize, Participation
from app.core.exceptions import DomainRuleException
from app.services.audit_service import log_audit

MANDATORY_LEGAL_KEYS = [
    "legal_promoter_ok",
    "participant_compliance_ok",
    "prizes_funded_ok",
    "rules_approved_ok",
    "lgpd_declared_ok",
    "electoral_cleared_ok",
]

LEGAL_LABELS = {
    "legal_promoter_ok": "Promotor legal identificado e habilitado",
    "participant_compliance_ok": "Regularidade dos boxes participantes",
    "prizes_funded_ok": "Premiação com origem de recursos comprovada",
    "rules_approved_ok": "Regulamento aprovado pelo órgão competente",
    "lgpd_declared_ok": "Tratamento de dados pessoais (LGPD) declarado",
    "electoral_cleared_ok": "Conformidade com o calendário eleitoral",
}

# Regras de aproximação disponíveis. Nenhuma é escolhida automaticamente para campanhas novas:
# o gestor precisa selecionar a que está escrita no regulamento aprovado.
APPROXIMATION_RULES = {
    "SOMENTE_EXATO": "Somente número idêntico ao apurado; sem correspondência, o prêmio não é atribuído nesta extração.",
    "SUPERIOR_DEPOIS_INFERIOR": "Número idêntico; não havendo, o imediatamente superior; não havendo superior, o imediatamente inferior.",
    "MAIS_PROXIMO": "Número idêntico; não havendo, o de menor distância numérica (empate: o superior). Regra herdada do MVP.",
}

VALID_TRANSITIONS = {
    "EM_ELABORACAO": ["AGUARDANDO_APROVACAO", "CANCELADA"],
    "AGUARDANDO_APROVACAO": ["APROVADA", "EM_ELABORACAO", "CANCELADA"],
    "APROVADA": ["ATIVA", "EM_ELABORACAO", "CANCELADA"],
    "ATIVA": ["ENCERRADA", "CANCELADA"],
    "ENCERRADA": [],
    "CANCELADA": [],
}

STATUS_LABELS = {
    "EM_ELABORACAO": "Em elaboração",
    "AGUARDANDO_APROVACAO": "Aguardando aprovação",
    "APROVADA": "Aprovada",
    "ATIVA": "Ativa",
    "ENCERRADA": "Encerrada",
    "CANCELADA": "Cancelada",
}

EDITABLE_STATUSES = {"EM_ELABORACAO"}


def get_campaign_or_404(db: Session, campaign_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise DomainRuleException("Campanha não encontrada.", status_code=404)
    return campaign


def validate_dates(data: Dict[str, Any]):
    s, e = data["start_date"], data["end_date"]
    ps, pe, re_ = data["purchase_start_date"], data["purchase_end_date"], data["registration_end_date"]
    if s >= e:
        raise DomainRuleException("O início da campanha precisa ser anterior ao término.")
    if ps > pe:
        raise DomainRuleException("O início do período de compras precisa ser anterior ao fim.")
    if ps < s or pe > e:
        raise DomainRuleException("O período de compras precisa estar dentro do período da campanha.")
    if re_ < pe:
        raise DomainRuleException("O cadastro de comprovantes deve ficar aberto até pelo menos o fim das compras.")
    if re_ > e:
        raise DomainRuleException("O prazo de cadastro de comprovantes não pode passar do término da campanha.")


def _apply_fields(campaign: Campaign, data: Dict[str, Any]):
    for field in ["name", "description", "start_date", "end_date", "purchase_start_date", "purchase_end_date",
                  "registration_end_date", "min_purchase_value", "max_numbers_per_cpf", "legal_promoter_name",
                  "legal_promoter_doc", "draw_method", "draw_approximation_rule", "regulation_reference",
                  "regulation_url", "regulation_notes"]:
        if field in data and data[field] is not None:
            setattr(campaign, field, data[field])
    if campaign.draw_approximation_rule and campaign.draw_approximation_rule not in APPROXIMATION_RULES:
        raise DomainRuleException("Regra de apuração desconhecida.")


def _replace_prizes(db: Session, campaign: Campaign, prizes: Optional[List[Dict[str, Any]]]):
    if prizes is None:
        return
    for p in list(campaign.prizes):
        db.delete(p)
    db.flush()
    for i, p in enumerate(prizes, start=1):
        if not (p.get("title") or "").strip():
            raise DomainRuleException(f"Informe a descrição do {i}º prêmio.")
        db.add(CampaignPrize(campaign_id=campaign.id, position=i, title=p["title"].strip(),
                             description=p.get("description"), estimated_value=p.get("estimated_value"),
                             draw_date=p.get("draw_date")))
    db.flush()


def create_campaign(db: Session, data: Dict[str, Any], user_id: int, username: str) -> Campaign:
    validate_dates(data)
    campaign = Campaign(status="EM_ELABORACAO", legal_checklist_json=json.dumps({k: False for k in MANDATORY_LEGAL_KEYS}))
    _apply_fields(campaign, {**{"min_purchase_value": 20.0, "max_numbers_per_cpf": 50, "draw_method": "LOTERIA_FEDERAL"}, **data})
    db.add(campaign)
    db.flush()
    _replace_prizes(db, campaign, data.get("prizes"))
    log_audit(db, "CAMPAIGN_CREATED", "Campaign", entity_id=campaign.id, user_id=user_id, username=username,
              campaign_id=campaign.id, after_state={"name": campaign.name, "status": campaign.status})
    db.commit()
    db.refresh(campaign)
    return campaign


def update_campaign(db: Session, campaign_id: int, data: Dict[str, Any], user_id: int, username: str) -> Campaign:
    campaign = get_campaign_or_404(db, campaign_id)
    if campaign.status not in EDITABLE_STATUSES:
        raise DomainRuleException(
            f"Campanhas na situação '{STATUS_LABELS[campaign.status]}' não podem ser editadas. "
            "Para corrigir, devolva a campanha para elaboração (antes da ativação).")
    before = serialize_campaign(campaign, brief=True)
    merged = {k: getattr(campaign, k) for k in ["start_date", "end_date", "purchase_start_date",
                                                  "purchase_end_date", "registration_end_date"]}
    merged.update({k: v for k, v in data.items() if v is not None and k in merged})
    validate_dates(merged)
    _apply_fields(campaign, data)
    _replace_prizes(db, campaign, data.get("prizes"))
    log_audit(db, "CAMPAIGN_UPDATED", "Campaign", entity_id=campaign.id, user_id=user_id, username=username,
              campaign_id=campaign.id, before_state=before, after_state=serialize_campaign(campaign, brief=True))
    db.commit()
    db.refresh(campaign)
    return campaign


def get_readiness(campaign: Campaign) -> List[Dict[str, Any]]:
    """Etapas da campanha com o que está completo e o que falta. Base do indicador de progresso."""
    checklist = json.loads(campaign.legal_checklist_json or "{}")
    steps = []

    def step(key, title, missing):
        steps.append({"key": key, "title": title, "done": not missing, "missing": missing})

    m = []
    if not (campaign.name or "").strip():
        m.append("Nome da campanha")
    if not (campaign.description or "").strip():
        m.append("Descrição / objetivo")
    if not (campaign.legal_promoter_name or "").strip():
        m.append("Promotor legal")
    if not (campaign.legal_promoter_doc or "").strip():
        m.append("CNPJ do promotor")
    step("geral", "Informações gerais", m)

    m = []
    try:
        validate_dates({"start_date": campaign.start_date, "end_date": campaign.end_date,
                        "purchase_start_date": campaign.purchase_start_date,
                        "purchase_end_date": campaign.purchase_end_date,
                        "registration_end_date": campaign.registration_end_date})
    except DomainRuleException as exc:
        m.append(exc.detail)
    step("periodo", "Período e calendário", m)

    m = []
    if not campaign.min_purchase_value or campaign.min_purchase_value <= 0:
        m.append("Valor mínimo de compra")
    if not campaign.max_numbers_per_cpf or campaign.max_numbers_per_cpf < 1:
        m.append("Limite de números por CPF")
    if not campaign.draw_approximation_rule:
        m.append("Regra de apuração conforme o regulamento")
    step("regras", "Regras de participação", m)

    step("premios", "Premiações", [] if campaign.prizes else ["Cadastre ao menos um prêmio"])
    step("regulamento", "Regulamento e documentação",
         [] if (campaign.regulation_reference or "").strip() else ["Referência do regulamento aprovado"])
    step("juridico", "Aprovação jurídica",
         [LEGAL_LABELS[k] for k in MANDATORY_LEGAL_KEYS if not checklist.get(k)])
    step("ativacao", "Publicação e ativação",
         [] if campaign.status in ("ATIVA", "ENCERRADA") else ["Ativar a campanha"])
    return steps


def _require_steps(campaign: Campaign, keys: List[str], action: str):
    pending = [s for s in get_readiness(campaign) if s["key"] in keys and not s["done"]]
    if pending:
        detail = "; ".join(f"{s['title']}: {', '.join(s['missing'])}" for s in pending)
        raise DomainRuleException(f"Não é possível {action}. Pendências — {detail}")


def register_legal_approvals(db: Session, campaign_id: int, approval_data: Dict[str, Any], user_id: int,
                             username: str) -> Campaign:
    campaign = get_campaign_or_404(db, campaign_id)
    if campaign.status != "AGUARDANDO_APROVACAO":
        raise DomainRuleException("A aprovação jurídica só pode ser registrada com a campanha aguardando aprovação. "
                                  "Envie a campanha para aprovação primeiro.")
    before = json.loads(campaign.legal_checklist_json or "{}")
    checklist = {key: bool(approval_data.get(key, False)) for key in MANDATORY_LEGAL_KEYS}
    campaign.legal_checklist_json = json.dumps(checklist)
    campaign.legal_promoter_name = approval_data.get("legal_promoter_name") or campaign.legal_promoter_name
    campaign.legal_promoter_doc = approval_data.get("legal_promoter_doc") or campaign.legal_promoter_doc
    campaign.legal_approval_justification = approval_data.get("justification")

    if all(checklist.values()):
        campaign.status = "APROVADA"
        campaign.approved_by_user_id = user_id
        campaign.approved_at = datetime.utcnow()

    log_audit(db, "CAMPAIGN_LEGAL_APPROVAL", "Campaign", entity_id=campaign.id, user_id=user_id, username=username,
              campaign_id=campaign.id, before_state={"checklist": before},
              after_state={"checklist": checklist, "new_status": campaign.status,
                           "justification": approval_data.get("justification")})
    db.commit()
    db.refresh(campaign)
    return campaign


def transition_campaign_status(db: Session, campaign_id: int, target_status: str, user_id: int, username: str,
                               justification: Optional[str] = None) -> Campaign:
    campaign = get_campaign_or_404(db, campaign_id)
    current = campaign.status
    if target_status not in VALID_TRANSITIONS.get(current, []):
        allowed = ", ".join(STATUS_LABELS[s] for s in VALID_TRANSITIONS.get(current, [])) or "nenhuma"
        raise DomainRuleException(
            f"Transição inválida de '{STATUS_LABELS.get(current, current)}' para "
            f"'{STATUS_LABELS.get(target_status, target_status)}'. Permitidas: {allowed}.")

    if target_status in ("CANCELADA", "EM_ELABORACAO") and current != "EM_ELABORACAO":
        if not justification or len(justification.strip()) < 10:
            raise DomainRuleException("Informe uma justificativa (mínimo 10 caracteres) para esta mudança.")

    if target_status == "AGUARDANDO_APROVACAO":
        _require_steps(campaign, ["geral", "periodo", "regras", "premios", "regulamento"], "enviar para aprovação")

    if target_status == "EM_ELABORACAO":
        # Volta para ajustes: a aprovação anterior deixa de valer.
        campaign.legal_checklist_json = json.dumps({k: False for k in MANDATORY_LEGAL_KEYS})
        campaign.approved_at = None
        campaign.approved_by_user_id = None

    if target_status == "ATIVA":
        _require_steps(campaign, ["geral", "periodo", "regras", "premios", "regulamento", "juridico"], "ativar")
        if datetime.utcnow() > campaign.end_date:
            raise DomainRuleException("Não é possível ativar uma campanha cujo término já passou.")
        campaign.activated_at = datetime.utcnow()

    if target_status == "ENCERRADA":
        campaign.closed_at = datetime.utcnow()

    if target_status == "CANCELADA" and db.query(Participation).filter(Participation.campaign_id == campaign.id).count():
        # Cancelamento com participações é permitido, mas fica destacado na auditoria.
        justification = f"[CAMPANHA COM PARTICIPAÇÕES] {justification}"

    campaign.status = target_status
    log_audit(db, "CAMPAIGN_STATUS_TRANSITION", "Campaign", entity_id=campaign.id, user_id=user_id,
              username=username, campaign_id=campaign.id, before_state={"status": current},
              after_state={"status": target_status, "justification": justification})
    db.commit()
    db.refresh(campaign)
    return campaign


def serialize_campaign(c: Campaign, brief: bool = False) -> Dict[str, Any]:
    iso = lambda d: d.isoformat() if d else None
    data = {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "status": c.status,
        "status_label": STATUS_LABELS.get(c.status, c.status),
        "start_date": iso(c.start_date),
        "end_date": iso(c.end_date),
        "purchase_start_date": iso(c.purchase_start_date),
        "purchase_end_date": iso(c.purchase_end_date),
        "registration_end_date": iso(c.registration_end_date),
        "min_purchase_value": c.min_purchase_value,
        "max_numbers_per_cpf": c.max_numbers_per_cpf,
        "legal_promoter_name": c.legal_promoter_name,
        "legal_promoter_doc": c.legal_promoter_doc,
        "draw_method": c.draw_method,
        "draw_approximation_rule": c.draw_approximation_rule,
        "regulation_reference": c.regulation_reference,
        "regulation_url": c.regulation_url,
        "regulation_notes": c.regulation_notes,
    }
    if brief:
        return data
    data.update({
        "legal_checklist": json.loads(c.legal_checklist_json or "{}"),
        "legal_labels": LEGAL_LABELS,
        "legal_approval_justification": c.legal_approval_justification,
        "approved_at": iso(c.approved_at),
        "activated_at": iso(c.activated_at),
        "closed_at": iso(c.closed_at),
        "created_at": iso(c.created_at),
        "lucky_numbers_issued": c.lucky_number_seq,
        "prizes": [{"id": p.id, "position": p.position, "title": p.title, "description": p.description,
                    "estimated_value": p.estimated_value, "draw_date": iso(p.draw_date)} for p in c.prizes],
        "readiness": get_readiness(c),
        "allowed_transitions": VALID_TRANSITIONS.get(c.status, []),
        "is_demo": (c.regulation_reference or "").startswith("DEMONSTRAÇÃO"),
    })
    return data
