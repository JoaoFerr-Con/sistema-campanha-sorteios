"""Apuração com base na Loteria Federal: congelamento da base, cálculo reproduzível, anulação formal e ata.

Pontos que dependem do regulamento aprovado estão documentados em DIAGNOSTICO.md (seção Apuração).
"""
import bisect
import hashlib
import html
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.entities import (
    Campaign, Participation, DrawResult, DrawBaseSnapshot, CampaignPrize, PrizeDeliveryEvent, Voucher,
)
from app.core.exceptions import DomainRuleException
from app.services.audit_service import log_audit, mask_cpf
from app.services.campaign_service import APPROXIMATION_RULES, get_campaign_or_404

UNIVERSE = 100_000  # números de 00000 a 99999 (5 dígitos formados pelas unidades dos 5 prêmios)
CALC_RULE_TEXT = "Unidade simples do 1º ao 5º prêmio da Loteria Federal, lidas de cima para baixo"
DELIVERY_STATUSES = ["PENDENTE", "CONTATADO", "ENTREGUE", "NAO_LOCALIZADO", "RECUSADO"]


# ---------------------------------------------------------------- base de participações

def _base_rows(db: Session, campaign_id: int) -> List[Participation]:
    return (db.query(Participation).filter(Participation.campaign_id == campaign_id)
            .order_by(Participation.lucky_number.asc()).all())


def canonical_base_csv(db: Session, campaign_id: int) -> str:
    """Arquivo canônico da base. O SHA-256 é calculado exatamente sobre este conteúdo (UTF-8),
    o que permite a qualquer auditor baixar o arquivo e conferir o hash publicado."""
    lines = ["numero_da_sorte;comprovante;participante_id;cpf_mascarado;box;validado_em_utc"]
    for p in _base_rows(db, campaign_id):
        lines.append(";".join([
            p.lucky_number,
            p.voucher.full_code,
            str(p.participant_id),
            mask_cpf(p.participant.document_cpf),
            p.voucher.box.box_number if p.voucher.box else "",
            p.validated_at.strftime("%Y-%m-%dT%H:%M:%S"),
        ]))
    return "\n".join(lines) + "\n"


def compute_base_hash(db: Session, campaign_id: int) -> Tuple[str, int]:
    csv_text = canonical_base_csv(db, campaign_id)
    return hashlib.sha256(csv_text.encode("utf-8")).hexdigest(), csv_text.count("\n") - 1


def freeze_and_hash_campaign_participations(db: Session, campaign_id: int) -> str:
    """Compatibilidade: devolve o hash atual da base."""
    digest, count = compute_base_hash(db, campaign_id)
    if count == 0:
        raise DomainRuleException("Não existem participações validadas nesta campanha para apuração.")
    return digest


def freeze_base(db: Session, campaign_id: int, user_id: int, username: str) -> DrawBaseSnapshot:
    campaign = get_campaign_or_404(db, campaign_id)
    if campaign.status != "ENCERRADA":
        raise DomainRuleException("Encerre a campanha antes de congelar a base: só assim novas participações são impedidas.")
    if db.query(DrawBaseSnapshot).filter(DrawBaseSnapshot.campaign_id == campaign_id).first():
        raise DomainRuleException("A base desta campanha já foi congelada.", status_code=409)
    digest, count = compute_base_hash(db, campaign_id)
    if count == 0:
        raise DomainRuleException("Não há participações validadas nesta campanha.")
    rows = _base_rows(db, campaign_id)
    snap = DrawBaseSnapshot(campaign_id=campaign_id, participations_count=count, sha256=digest,
                            first_lucky_number=rows[0].lucky_number, last_lucky_number=rows[-1].lucky_number,
                            frozen_by_user_id=user_id, frozen_by_username=username)
    db.add(snap)
    log_audit(db, "DRAW_BASE_FROZEN", "DrawBaseSnapshot", entity_id=campaign_id, user_id=user_id,
              username=username, campaign_id=campaign_id,
              after_state={"participations": count, "sha256": digest})
    db.commit()
    db.refresh(snap)
    return snap


def integrity_status(db: Session, campaign_id: int) -> Dict[str, Any]:
    snap = db.query(DrawBaseSnapshot).filter(DrawBaseSnapshot.campaign_id == campaign_id).first()
    current, count = compute_base_hash(db, campaign_id)
    return {
        "frozen": bool(snap),
        "snapshot": {
            "sha256": snap.sha256, "participations_count": snap.participations_count,
            "first_lucky_number": snap.first_lucky_number, "last_lucky_number": snap.last_lucky_number,
            "frozen_at": snap.frozen_at.isoformat(), "frozen_by": snap.frozen_by_username,
        } if snap else None,
        "current_sha256": current,
        "current_count": count,
        "intact": (snap.sha256 == current) if snap else None,
    }


# ---------------------------------------------------------------- cálculo

def parse_extraction(prizes: List[str]) -> List[str]:
    if len(prizes) != 5:
        raise DomainRuleException("Informe os 5 primeiros prêmios da extração da Loteria Federal.")
    clean = []
    for i, p in enumerate(prizes, start=1):
        digits = re.sub(r"[\s.]", "", str(p or ""))
        if not re.fullmatch(r"\d{5}", digits):
            raise DomainRuleException(f"O {i}º prêmio deve ter exatamente 5 algarismos (ex.: 07.815). Recebido: '{p}'.")
        clean.append(digits)  # zeros à esquerda preservados por serem texto
    return clean


def target_from_extraction(clean_prizes: List[str]) -> str:
    return "".join(p[-1] for p in clean_prizes)


def pick_winner(numbers: List[int], target: int, rule: str) -> Tuple[Optional[int], str, Optional[int]]:
    """Retorna (número vencedor, tipo de correspondência, distância). `numbers` deve estar ordenado."""
    if not numbers:
        return None, "SEM_PARTICIPACOES", None
    i = bisect.bisect_left(numbers, target)
    if i < len(numbers) and numbers[i] == target:
        return target, "EXATO", 0
    if rule == "SOMENTE_EXATO":
        return None, "SEM_CORRESPONDENCIA", None
    sup = numbers[i] if i < len(numbers) else None
    inf = numbers[i - 1] if i > 0 else None
    if rule == "SUPERIOR_DEPOIS_INFERIOR":
        chosen = sup if sup is not None else inf
    elif rule == "MAIS_PROXIMO":
        if sup is None:
            chosen = inf
        elif inf is None:
            chosen = sup
        else:
            chosen = sup if (sup - target) <= (target - inf) else inf  # empate: superior
    else:
        raise DomainRuleException("Regra de apuração não configurada na campanha.")
    return chosen, "APROXIMADO", abs(chosen - target)


def concentration(numbers: List[int], rule: Optional[str]) -> Optional[Dict[str, Any]]:
    """Mede quanto a regra concentra a chance em poucos números (risco de equidade).

    Para cada número participante calcula a fração dos 100.000 resultados possíveis que o tornam
    vencedor. Com numeração sequencial a partir de 00001 e aproximação, o último número tende a
    concentrar quase toda a chance.
    """
    if not numbers or not rule:
        return None
    n = len(numbers)
    shares = []
    if rule == "SOMENTE_EXATO":
        shares = [1] * n
    elif rule == "SUPERIOR_DEPOIS_INFERIOR":
        prev = -1
        for k, a in enumerate(numbers):
            cover = a - prev
            if k == n - 1:
                cover += (UNIVERSE - 1) - a
            shares.append(cover)
            prev = a
    elif rule == "MAIS_PROXIMO":
        bounds = [0]
        for a, b in zip(numbers, numbers[1:]):
            # menor alvo que leva ao superior b (empate vai para o superior)
            bounds.append((a + b + 1) // 2)
        bounds.append(UNIVERSE)
        shares = [bounds[k + 1] - bounds[k] for k in range(n)]
    else:
        return None
    top = max(range(n), key=lambda k: shares[k])
    no_winner = UNIVERSE - sum(shares)
    return {
        "participants": n,
        "fair_share_pct": round(100 / n, 4),
        "top_number": f"{numbers[top]:05d}",
        "top_share_pct": round(100 * shares[top] / UNIVERSE, 4),
        "no_winner_pct": round(100 * no_winner / UNIVERSE, 4),
        "is_concentrated": shares[top] / UNIVERSE > 5 * (1 / n) and n > 1,
    }


# ---------------------------------------------------------------- execução

def execute_federal_lottery_draw(db: Session, campaign_id: int, contest_number: str, draw_date: datetime,
                                 extraction_prizes: List[str], prize_title: Optional[str], user_id: int,
                                 username: str, prize_id: Optional[int] = None) -> Dict[str, Any]:
    campaign = get_campaign_or_404(db, campaign_id)
    if campaign.status != "ENCERRADA":
        raise DomainRuleException("A apuração só pode ser feita com a campanha encerrada e a base congelada.")
    if not campaign.draw_approximation_rule:
        raise DomainRuleException("A campanha não tem regra de apuração definida conforme o regulamento.")
    integrity = integrity_status(db, campaign_id)
    if not integrity["frozen"]:
        raise DomainRuleException("Congele a base de participações antes de apurar.")
    if not integrity["intact"]:
        raise DomainRuleException("A base atual difere da base congelada (hash divergente). Apuração bloqueada.", status_code=409)
    if not (contest_number or "").strip().isdigit():
        raise DomainRuleException("Informe o número do concurso da Loteria Federal (somente algarismos).")

    prize = None
    if prize_id:
        prize = db.query(CampaignPrize).filter(CampaignPrize.id == prize_id, CampaignPrize.campaign_id == campaign_id).first()
        if not prize:
            raise DomainRuleException("Prêmio não pertence a esta campanha.", status_code=404)
    elif campaign.prizes:
        raise DomainRuleException("Selecione qual prêmio está sendo apurado.")
    if prize and db.query(DrawResult).filter(DrawResult.prize_id == prize.id, DrawResult.status == "VALIDO").first():
        raise DomainRuleException("Este prêmio já foi apurado. Para refazer, anule a apuração anterior com justificativa.",
                                  status_code=409)

    clean = parse_extraction(extraction_prizes)
    target = target_from_extraction(clean)
    rule = campaign.draw_approximation_rule
    rows = _base_rows(db, campaign_id)
    by_number = {int(p.lucky_number): p for p in rows}
    numbers = sorted(by_number)
    win_num, match_type, distance = pick_winner(numbers, int(target), rule)
    winner = by_number.get(win_num) if win_num is not None else None

    previous_wins = []
    if winner:
        previous_wins = [r.prize_title for r in db.query(DrawResult).filter(
            DrawResult.campaign_id == campaign_id, DrawResult.status == "VALIDO").all()
            if r.winning_participation and r.winning_participation.participant_id == winner.participant_id]

    title = prize.title if prize else (prize_title or "Prêmio")
    draw_entry = DrawResult(
        campaign_id=campaign_id, draw_date=draw_date, federal_lottery_contest_number=contest_number.strip(),
        federal_lottery_extraction_json=json.dumps(clean), consolidated_base_sha256=integrity["snapshot"]["sha256"],
        calculation_rule=CALC_RULE_TEXT, winner_lucky_number=f"{win_num:05d}" if win_num is not None else "—",
        winning_participation_id=winner.id if winner else None, prize_id=prize.id if prize else None,
        prize_title=title, target_number=target, match_type=match_type, approximation_rule=rule,
        distance=distance, status="VALIDO", executed_by_user_id=user_id, executed_by_username=username,
        delivery_status="PENDENTE" if winner else "SEM_CONTEMPLADO",
        delivery_notes="Aguardando contato formal com o contemplado conforme regulamento." if winner else None,
    )
    db.add(draw_entry)
    db.flush()
    log_audit(db, "DRAW_EXECUTED_LOTERIA_FEDERAL", "DrawResult", entity_id=draw_entry.id, user_id=user_id,
              username=username, campaign_id=campaign_id,
              after_state={"contest": contest_number, "extraction": clean, "target": target, "rule": rule,
                           "match_type": match_type, "winning_lucky_number": draw_entry.winner_lucky_number,
                           "base_sha256": draw_entry.consolidated_base_sha256, "prize": title})
    db.commit()
    db.refresh(draw_entry)
    result = serialize_result(draw_entry, include_contact=True)
    result.update({"status": "success", "message": "Apuração registrada.",
                   "calculated_target_number": target, "previous_wins_same_participant": previous_wins})
    return result


def annul_draw(db: Session, draw_id: int, reason: str, user_id: int, username: str) -> DrawResult:
    draw = db.query(DrawResult).filter(DrawResult.id == draw_id).first()
    if not draw:
        raise DomainRuleException("Apuração não encontrada.", status_code=404)
    if draw.status == "ANULADO":
        raise DomainRuleException("Esta apuração já foi anulada.")
    if draw.delivery_status == "ENTREGUE":
        raise DomainRuleException("O prêmio já foi entregue; a apuração não pode ser anulada pelo sistema.")
    if not reason or len(reason.strip()) < 20:
        raise DomainRuleException("A anulação exige justificativa formal (mínimo 20 caracteres), "
                                  "com referência ao documento que a autoriza.")
    draw.status = "ANULADO"
    draw.annulled_reason = reason.strip()
    draw.annulled_by_username = username
    draw.annulled_at = datetime.utcnow()
    log_audit(db, "DRAW_ANNULLED", "DrawResult", entity_id=draw.id, user_id=user_id, username=username,
              campaign_id=draw.campaign_id, before_state={"status": "VALIDO", "winner": draw.winner_lucky_number},
              after_state={"status": "ANULADO", "reason": reason})
    db.commit()
    db.refresh(draw)
    return draw


def update_delivery(db: Session, draw_id: int, status: str, notes: Optional[str], user_id: int, username: str) -> DrawResult:
    draw = db.query(DrawResult).filter(DrawResult.id == draw_id).first()
    if not draw:
        raise DomainRuleException("Registro de apuração não encontrado.", status_code=404)
    if draw.status != "VALIDO" or not draw.winning_participation_id:
        raise DomainRuleException("Só é possível registrar entrega de apurações válidas com contemplado.")
    if status not in DELIVERY_STATUSES:
        raise DomainRuleException("Situação de entrega inválida.")
    if draw.delivery_status == "ENTREGUE":
        raise DomainRuleException("A entrega já foi registrada e não pode ser alterada.")
    before = draw.delivery_status
    draw.delivery_status = status
    if notes:
        draw.delivery_notes = notes
    db.add(PrizeDeliveryEvent(draw_id=draw.id, status=status, notes=notes, username=username))
    log_audit(db, "PRIZE_DELIVERY_UPDATED", "DrawResult", entity_id=draw.id, user_id=user_id, username=username,
              campaign_id=draw.campaign_id, before_state={"delivery_status": before},
              after_state={"delivery_status": status, "notes": notes})
    db.commit()
    db.refresh(draw)
    return draw


def serialize_result(r: DrawResult, include_contact: bool = False) -> Dict[str, Any]:
    wp = r.winning_participation
    data = {
        "id": r.id,
        "campaign_id": r.campaign_id,
        "prize_id": r.prize_id,
        "prize_title": r.prize_title,
        "draw_date": r.draw_date.isoformat(),
        "contest_number": r.federal_lottery_contest_number,
        "extraction": json.loads(r.federal_lottery_extraction_json),
        "extraction_json": r.federal_lottery_extraction_json,
        "consolidated_base_sha256": r.consolidated_base_sha256,
        "calculation_rule": r.calculation_rule,
        "approximation_rule": r.approximation_rule,
        "approximation_rule_text": APPROXIMATION_RULES.get(r.approximation_rule or "", ""),
        "target_number": r.target_number,
        "match_type": r.match_type,
        "distance": r.distance,
        "winner_lucky_number": r.winner_lucky_number,
        "status": r.status,
        "executed_by": r.executed_by_username,
        "created_at": r.created_at.isoformat(),
        "annulled_reason": r.annulled_reason,
        "annulled_by": r.annulled_by_username,
        "annulled_at": r.annulled_at.isoformat() if r.annulled_at else None,
        "delivery_status": r.delivery_status,
        "delivery_notes": r.delivery_notes,
        "delivery_events": [{"status": e.status, "notes": e.notes, "username": e.username,
                             "created_at": e.created_at.isoformat()} for e in r.delivery_events],
        "winner_name": wp.participant.full_name if wp else "",
        "winner_cpf_masked": mask_cpf(wp.participant.document_cpf) if wp else "",
        "voucher_code": wp.voucher.full_code if wp else "",
        "box_number": wp.voucher.box.box_number if wp and wp.voucher.box else "",
        "permissionario": wp.voucher.permissionario.name if wp and wp.voucher.permissionario else "",
    }
    if include_contact and wp:
        data["winner_details"] = {"name": wp.participant.full_name, "cpf_masked": mask_cpf(wp.participant.document_cpf),
                                  "phone": wp.participant.phone, "neighborhood": wp.participant.neighborhood}
        data["voucher_details"] = {"code": data["voucher_code"], "box_number": data["box_number"],
                                   "permissionario": data["permissionario"]}
    return data


def draw_overview(db: Session, campaign_id: int) -> Dict[str, Any]:
    campaign = get_campaign_or_404(db, campaign_id)
    numbers = sorted(int(p.lucky_number) for p in _base_rows(db, campaign_id))
    results = db.query(DrawResult).filter(DrawResult.campaign_id == campaign_id).order_by(DrawResult.id.asc()).all()
    return {
        "campaign": {"id": campaign.id, "name": campaign.name, "status": campaign.status,
                     "rule": campaign.draw_approximation_rule,
                     "rule_text": APPROXIMATION_RULES.get(campaign.draw_approximation_rule or "", None),
                     "closed_at": campaign.closed_at.isoformat() if campaign.closed_at else None},
        "eligible_count": len(numbers),
        "unique_participants": db.query(Participation.participant_id).filter(
            Participation.campaign_id == campaign_id).distinct().count(),
        "integrity": integrity_status(db, campaign_id),
        "concentration": concentration(numbers, campaign.draw_approximation_rule),
        "prizes": [{"id": p.id, "position": p.position, "title": p.title,
                    "draw_date": p.draw_date.isoformat() if p.draw_date else None,
                    "drawn": any(r.prize_id == p.id and r.status == "VALIDO" for r in results)} for p in campaign.prizes],
        "results": [serialize_result(r) for r in results],
    }


# ---------------------------------------------------------------- documentação

def render_minutes_html(db: Session, campaign_id: int, issued_by: str) -> str:
    """Ata de apuração em HTML imprimível (o navegador salva em PDF)."""
    ov = draw_overview(db, campaign_id)
    c = get_campaign_or_404(db, campaign_id)
    e = html.escape
    fmt = lambda iso: datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M") + " UTC" if iso else "—"
    integ = ov["integrity"]
    snap = integ["snapshot"] or {}
    rows = ""
    for r in ov["results"]:
        rows += f"""<tr class="{'anulado' if r['status']=='ANULADO' else ''}">
<td>{e(r['prize_title'])}</td><td>{e(r['contest_number'])}<br><small>{fmt(r['draw_date'])[:10]}</small></td>
<td>{' · '.join(e(x) for x in r['extraction'])}</td><td><b>{e(r['target_number'] or '')}</b></td>
<td><b>{e(r['winner_lucky_number'])}</b><br><small>{e(r['match_type'] or '')}{f" (distância {r['distance']})" if r['distance'] else ''}</small></td>
<td>{e(r['winner_name'])}<br><small>{e(r['winner_cpf_masked'])} · comprovante {e(r['voucher_code'])} · box {e(r['box_number'])}</small></td>
<td>{e(r['status'])}{('<br><small>' + e(r['annulled_reason'] or '') + '</small>') if r['status']=='ANULADO' else ''}</td></tr>"""
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Ata de apuração — {e(c.name)}</title>
<style>body{{font-family:Georgia,serif;max-width:900px;margin:32px auto;color:#1b2733;line-height:1.5;padding:0 16px}}
h1{{font-size:22px;margin:0}}header{{border-bottom:2px solid #0f5e57;padding-bottom:12px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}}td,th{{border:1px solid #cfd8dc;padding:6px;text-align:left;vertical-align:top}}
th{{background:#eef3f3}}.hash{{font-family:monospace;word-break:break-all;font-size:12px}}tr.anulado{{color:#8a8a8a;text-decoration:line-through}}
small{{color:#5d6b78}}.sign{{display:flex;gap:40px;margin-top:60px}}.sign div{{flex:1;border-top:1px solid #1b2733;text-align:center;padding-top:6px;font-size:13px}}
@media print{{button{{display:none}}}}</style></head><body>
<button onclick="window.print()">Imprimir / salvar em PDF</button>
<header><div>Prefeitura Municipal de Barcarena — SEICOMTEC</div><h1>Ata de apuração</h1>
<div>{e(c.name)}</div></header>
<p><b>Promotor:</b> {e(c.legal_promoter_name or '—')} ({e(c.legal_promoter_doc or '—')})<br>
<b>Regulamento:</b> {e(c.regulation_reference or '—')}<br>
<b>Período de participação:</b> {c.purchase_start_date:%d/%m/%Y} a {c.registration_end_date:%d/%m/%Y} · <b>Encerrada em:</b> {fmt(ov['campaign']['closed_at'])}</p>
<h2>Base de participações</h2>
<p>Participações elegíveis: <b>{ov['eligible_count']}</b> · Consumidores únicos: <b>{ov['unique_participants']}</b><br>
Números: {e(snap.get('first_lucky_number') or '—')} a {e(snap.get('last_lucky_number') or '—')} · Congelada em {fmt(snap.get('frozen_at'))} por {e(snap.get('frozen_by') or '—')}</p>
<p>SHA-256 da base congelada:<br><span class="hash">{e(snap.get('sha256') or 'não congelada')}</span><br>
Verificação no momento da emissão: <b>{'íntegra' if integ['intact'] else ('DIVERGENTE' if integ['frozen'] else 'não congelada')}</b></p>
<h2>Regra aplicada</h2><p>{e(CALC_RULE_TEXT)}.<br>Aproximação: {e(ov['campaign']['rule_text'] or 'não definida')}</p>
<h2>Resultados</h2><table><tr><th>Prêmio</th><th>Concurso</th><th>Extração (1º a 5º)</th><th>Número apurado</th><th>Número contemplado</th><th>Contemplado</th><th>Situação</th></tr>{rows or '<tr><td colspan=7>Nenhuma apuração registrada.</td></tr>'}</table>
<p><small>Emitido em {datetime.utcnow():%d/%m/%Y %H:%M} UTC por {e(issued_by)}. O arquivo canônico da base pode ser baixado no sistema para conferência independente do hash.</small></p>
<div class="sign"><div>Responsável pela apuração</div><div>Representante jurídico</div><div>Testemunha</div></div>
</body></html>"""
