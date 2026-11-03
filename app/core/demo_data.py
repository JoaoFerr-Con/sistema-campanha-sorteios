"""Carga de demonstração (somente com DEMO_MODE=true).

Gera dados FICTÍCIOS para visualizar todas as funcionalidades:
* conferência da planilha: linhas sem divergência aprovadas; as com divergência ficam pendentes;
* campanhas em todas as situações (elaboração, aguardando aprovação, ativa, encerrada e apurada);
* talões distribuídos, comprovantes emitidos pelos boxes, ocorrências;
* consumidores e números da sorte ao longo dos últimos dias, recusas no balcão;
* uma apuração concluída com base congelada, ata e entrega do prêmio registrada.

Os nomes e CPFs dos consumidores são inventados (CPFs com dígitos válidos, gerados aleatoriamente).
Os comprovantes NATAL-00001 a NATAL-00050 do Box 260 ficam livres para testes no balcão.
"""
import json
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.entities import (
    User, Box, Permissionario, BoxOccupancy, Campaign, CampaignPrize, VoucherBatch, Voucher, Participant,
    Participation, ValidationAttempt, ImportStagingRow, PrizeDeliveryEvent,
)
from app.services.audit_service import log_audit, mask_cpf

MARKER_CAMPAIGN = "Dia das Mães 2026 — Mãe Merece"
FIRST = ["Ana", "Maria", "José", "João", "Francisca", "Antônio", "Raimunda", "Carlos", "Paulo", "Lucas", "Juliana",
         "Fernanda", "Rafael", "Patrícia", "Marcos", "Aline", "Bruna", "Diego", "Edson", "Gabriela", "Helena",
         "Igor", "Jéssica", "Kátia", "Leandro", "Mariana", "Nilson", "Odete", "Pedro", "Rosângela", "Sérgio",
         "Tatiane", "Valdir", "Wellington", "Yasmin", "Cleide", "Benedito", "Luzia", "Raimundo", "Socorro"]
LAST = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Rodrigues", "Almeida", "Nascimento",
        "Carvalho", "Ferreira", "Gomes", "Ribeiro", "Martins", "Araújo", "Barbosa", "Cardoso", "Monteiro", "Pinheiro",
        "Batista", "Moraes", "Teixeira", "Farias", "Cunha", "Brito", "Quaresma", "Tavares", "Pantoja", "Sarmento"]
BAIRROS = ["Vila dos Cabanos", "Centro", "Laranjal", "Itupanema", "Pioneiro", "São Francisco", "Novo Horizonte",
           "Murucupi", "Comercial", "Nova Vida"]


def _cpf(rng: random.Random) -> str:
    while True:
        base = [rng.randint(0, 9) for _ in range(9)]
        if len(set(base)) == 1:
            continue
        for n in (9, 10):
            s = sum(base[i] * ((n + 1) - i) for i in range(n))
            base.append((s * 10) % 11 % 10)
        return "".join(map(str, base))


def _phone(rng):
    return f"(91) 9{rng.randint(8000, 9999)}-{rng.randint(1000, 9999)}"


def populate_demo(db: Session):
    if db.query(Campaign).filter(Campaign.name == MARKER_CAMPAIGN).first():
        return
    rng = random.Random(2026)
    now = datetime.utcnow()
    admin = db.query(User).filter(User.username == "admin").first()
    att = db.query(User).filter(User.username == "atendente").first()

    # ---------------------------------------------------------------- equipe extra do balcão
    att2 = User(username="atendente2", password_hash=hash_password("password123"), full_name="Atendente do Balcão — Turno da tarde",
                role="ATENDENTE", is_active=True, is_demo=True)
    db.add(att2)
    db.flush()
    attendants = [att, att2]

    # ---------------------------------------------------------------- conferência da planilha
    from app.services.box_service import review_staging_row
    for row in db.query(ImportStagingRow).filter(ImportStagingRow.status == "PENDENTE_REVISAO").all():
        flags = json.loads(row.discrepancy_flags or "[]")
        if flags and flags != ["MARKED_VAGO"]:
            continue  # divergências reais ficam para o gestor revisar na demonstração
        review_staging_row(db, row.id, "APROVADO", "Carga de demonstração: linha sem divergência aprovada automaticamente.",
                           admin.id, "admin", is_vago=flags == ["MARKED_VAGO"])

    # permissionários irregulares, para mostrar bloqueios
    confirmed = (db.query(Box).filter(Box.official_status == "CONFIRMADO").all())
    occs = []
    for b in sorted(confirmed, key=lambda x: int(x.box_number)):
        occ = next((o for o in b.occupancies if o.is_current), None)
        if occ:
            occs.append(occ)
    irregular = [o for o in occs if o.box.box_number in ("44", "118", "301")]
    for o in irregular:
        o.permissionario.status = "SUSPENSO"
        log_audit(db, "PERMISSIONARIO_UPDATED", "Permissionario", entity_id=o.permissionario_id, user_id=admin.id,
                  username="admin", before_state={"status": "ATIVO"},
                  after_state={"status": "SUSPENSO", "justification": "Demonstração: termo de permissão vencido."})
    db.flush()
    active_occs = [o for o in occs if o.permissionario.status == "ATIVO" and o.box.box_number != "260"]

    # ---------------------------------------------------------------- campanhas
    checklist_ok = json.dumps({k: True for k in ["legal_promoter_ok", "participant_compliance_ok", "prizes_funded_ok",
                                                  "rules_approved_ok", "lgpd_declared_ok", "electoral_cleared_ok"]})
    promoter = dict(legal_promoter_name="Prefeitura Municipal de Barcarena — SEICOMTEC", legal_promoter_doc="05.105.200/0001-22")

    pilot = db.query(Campaign).filter(Campaign.name.like("Campanha Piloto%")).first()
    pilot.start_date = pilot.purchase_start_date = now - timedelta(days=14)
    pilot.activated_at = now - timedelta(days=14)
    pilot.approved_at = now - timedelta(days=16)
    if len(pilot.prizes) < 2:
        db.add(CampaignPrize(campaign_id=pilot.id, position=2, title="Vale-compras de R$ 1.000 no Complexo",
                             estimated_value=1000.0, draw_date=pilot.end_date + timedelta(days=1)))
        db.add(CampaignPrize(campaign_id=pilot.id, position=3, title="Smart TV 50 polegadas",
                             estimated_value=2600.0, draw_date=pilot.end_date + timedelta(days=1)))

    closed = Campaign(
        name=MARKER_CAMPAIGN, description="Campanha encerrada e já apurada — dados fictícios de demonstração.",
        start_date=datetime(2026, 4, 20), end_date=datetime(2026, 5, 20), purchase_start_date=datetime(2026, 4, 20),
        purchase_end_date=datetime(2026, 5, 10, 23), registration_end_date=datetime(2026, 5, 12, 23),
        min_purchase_value=30.0, max_numbers_per_cpf=20, status="ENCERRADA", legal_checklist_json=checklist_ok,
        legal_approval_justification="Parecer fictício de demonstração.", draw_approximation_rule="SUPERIOR_DEPOIS_INFERIOR",
        regulation_reference="DEMONSTRAÇÃO — regulamento fictício", approved_at=datetime(2026, 4, 15),
        activated_at=datetime(2026, 4, 20), closed_at=datetime(2026, 5, 13), approved_by_user_id=admin.id, **promoter)
    draft = Campaign(
        name="Festival do Abacaxi 2027", description="Rascunho: falta definir regulamento e premiação.",
        start_date=now + timedelta(days=90), end_date=now + timedelta(days=130), purchase_start_date=now + timedelta(days=90),
        purchase_end_date=now + timedelta(days=120), registration_end_date=now + timedelta(days=125),
        min_purchase_value=25.0, max_numbers_per_cpf=30, status="EM_ELABORACAO",
        legal_checklist_json=json.dumps({}), **promoter)
    waiting = Campaign(
        name="Volta às Aulas 2027", description="Enviada para análise jurídica. Prêmios: kits escolares e bicicletas.",
        start_date=now + timedelta(days=60), end_date=now + timedelta(days=100), purchase_start_date=now + timedelta(days=60),
        purchase_end_date=now + timedelta(days=90), registration_end_date=now + timedelta(days=95),
        min_purchase_value=20.0, max_numbers_per_cpf=25, status="AGUARDANDO_APROVACAO",
        legal_checklist_json=json.dumps({"legal_promoter_ok": True, "participant_compliance_ok": True, "lgpd_declared_ok": True}),
        draw_approximation_rule="SOMENTE_EXATO", regulation_reference="Processo 0312/2026 — em análise", **promoter)
    db.add_all([closed, draft, waiting])
    db.flush()
    db.add_all([
        CampaignPrize(campaign_id=closed.id, position=1, title="Geladeira frost free 400 L", estimated_value=3200.0, draw_date=datetime(2026, 5, 16, 22)),
        CampaignPrize(campaign_id=closed.id, position=2, title="Vale-compras de R$ 500", estimated_value=500.0, draw_date=datetime(2026, 5, 16, 22)),
        CampaignPrize(campaign_id=waiting.id, position=1, title="Bicicleta aro 26", estimated_value=900.0, draw_date=now + timedelta(days=101)),
        CampaignPrize(campaign_id=waiting.id, position=2, title="10 kits escolares", estimated_value=1500.0, draw_date=now + timedelta(days=101)),
    ])
    for c, when, st in [(closed, datetime(2026, 4, 1), "EM_ELABORACAO"), (draft, now - timedelta(days=3), "EM_ELABORACAO"),
                        (waiting, now - timedelta(days=6), "EM_ELABORACAO")]:
        log_audit(db, "CAMPAIGN_CREATED", "Campaign", entity_id=c.id, user_id=admin.id, username="admin", campaign_id=c.id,
                  after_state={"name": c.name, "status": st})
    log_audit(db, "CAMPAIGN_STATUS_TRANSITION", "Campaign", entity_id=waiting.id, user_id=admin.id, username="admin",
              campaign_id=waiting.id, before_state={"status": "EM_ELABORACAO"}, after_state={"status": "AGUARDANDO_APROVACAO"})

    # ---------------------------------------------------------------- consumidores
    people = []
    for _ in range(140):
        people.append(Participant(full_name=f"{rng.choice(FIRST)} {rng.choice(LAST)} {rng.choice(LAST)}", document_cpf=_cpf(rng),
                                  phone=_phone(rng), neighborhood=rng.choice(BAIRROS),
                                  created_at=now - timedelta(days=rng.randint(15, 200))))
    seen = set()
    people = [p for p in people if not (p.document_cpf in seen or seen.add(p.document_cpf))]
    db.add_all(people)
    db.flush()

    # ---------------------------------------------------------------- talões, emissões e participações
    def distribute(campaign, prefix, start, occ_list, size, when):
        batches, n = [], start
        latest = 0
        for occ in occ_list:
            latest += 1
            b = VoucherBatch(campaign_id=campaign.id, permissionario_id=occ.permissionario_id, box_id=occ.box_id,
                             batch_number=latest + (1 if campaign is pilot else 0), code_prefix=prefix, start_number=n,
                             end_number=n + size - 1, total_vouchers=size, distributed_by_user_id=admin.id, status="ATIVO",
                             distributed_at=when + timedelta(hours=rng.randint(0, 30)))
            db.add(b)
            db.flush()
            vs = [Voucher(batch_id=b.id, campaign_id=campaign.id, box_id=occ.box_id, permissionario_id=occ.permissionario_id,
                          full_code=f"{prefix}-{seq:05d}", sequence_number=seq, status="DISTRIBUIDO") for seq in range(n, n + size)]
            db.add_all(vs)
            log_audit(db, "BATCH_CREATED", "VoucherBatch", entity_id=b.id, user_id=admin.id, username="admin",
                      campaign_id=campaign.id, after_state={"batch_number": b.batch_number, "prefix": prefix,
                                                            "range": f"{n}..{n + size - 1}", "total": size,
                                                            "box": occ.box.box_number, "permissionario": occ.permissionario.name})
            batches.append((b, vs))
            n += size
        db.flush()
        return batches

    def participate(campaign, voucher, person, when, attendant):
        campaign.lucky_number_seq += 1
        voucher.status = "UTILIZADO"
        if voucher.issued_value is None and rng.random() < .6:
            voucher.issued_value = round(rng.uniform(campaign.min_purchase_value, 260), 2)
            voucher.issued_at = when - timedelta(hours=rng.randint(1, 48))
        p = Participation(campaign_id=campaign.id, voucher_id=voucher.id, participant_id=person.id, box_id=voucher.box_id,
                          permissionario_id=voucher.permissionario_id, attendant_user_id=attendant.id,
                          lucky_number=f"{campaign.lucky_number_seq:05d}", validated_at=when, created_at=when)
        db.add(p)
        db.add(ValidationAttempt(campaign_id=campaign.id, voucher_code=voucher.full_code, tried_by_user_id=attendant.id,
                                 participant_cpf=person.document_cpf, success=True, created_at=when))
        log_audit(db, "PARTICIPATION_VALIDATED", "Voucher", entity_id=voucher.id, user_id=attendant.id,
                  username=attendant.username, campaign_id=campaign.id,
                  after_state={"voucher_code": voucher.full_code, "lucky_number": p.lucky_number,
                               "participant_cpf": mask_cpf(person.document_cpf), "box_id": voucher.box_id})
        db.flush()
        db.query(type(p)).filter(type(p).id == p.id).update({"validated_at": when})  # mantém a data retroativa

    # campanha ativa (piloto): 24 boxes, 30 comprovantes cada, a partir de NATAL-00051
    pick = rng.sample(active_occs, min(24, len(active_occs)))
    pilot_batches = distribute(pilot, "NATAL", 51, pick, 30, now - timedelta(days=13))
    weights = [rng.uniform(.3, 1.6) for _ in pilot_batches]
    pool = []
    for (b, vs), w in zip(pilot_batches, weights):
        k = int(len(vs) * min(.85, .25 * w + .1))
        pool += vs[:k]
        for v in vs[k:k + 3]:  # alguns emitidos ao consumidor e ainda não levados ao balcão
            v.status = "EMITIDO"
            v.issued_value = round(rng.uniform(20, 180), 2)
            v.issued_at = now - timedelta(hours=rng.randint(2, 60))
            v.invoice_doc_number = f"NFC-e {rng.randint(1000, 9999)}"
    rng.shuffle(pool)
    regulars = rng.sample(people, 18)
    for i, v in enumerate(pool):
        day = min(13, int(rng.triangular(0, 13, 9)))
        when = now - timedelta(days=13 - day, hours=rng.randint(0, 9), minutes=rng.randint(0, 59))
        if when > now:
            when = now - timedelta(minutes=rng.randint(5, 300))
        person = rng.choice(regulars) if rng.random() < .35 else rng.choice(people)
        participate(pilot, v, person, when, rng.choice(attendants))

    # ocorrências e recusas
    for (b, vs) in pilot_batches[:5]:
        v = vs[-1]
        v.status = rng.choice(["EXTRAVIADO", "DEVOLVIDO", "CANCELADO"])
        log_audit(db, f"VOUCHER_INCIDENT_{v.status}", "Voucher", entity_id=v.id, username="permissionario",
                  campaign_id=pilot.id, before_state={"status": "DISTRIBUIDO"},
                  after_state={"status": v.status, "reason": "Demonstração: comunicado pelo box."})
    used = [v for v in pool[:12]]
    refusals = [(v.full_code, f"Comprovante '{v.full_code}' já foi utilizado e validado anteriormente.") for v in used[:7]]
    refusals += [(f"NATAL-{rng.randint(5000, 9000):05d}", None) for _ in range(5)]
    refusals = [(c, r or f"Comprovante '{c}' não existe no sistema.") for c, r in refusals]
    for (b, vs) in pilot_batches[:3]:
        refusals.append((vs[-1].full_code, f"Comprovante inválido para uso (situação: {vs[-1].status})."))
    if irregular:
        refusals.append(("NATAL-09901", "Permissionário do box com cadastro irregular (SUSPENSO)."))
    for code, reason in refusals:
        db.add(ValidationAttempt(campaign_id=pilot.id, voucher_code=code, tried_by_user_id=rng.choice(attendants).id,
                                 participant_cpf=rng.choice(people).document_cpf, success=False, refusal_reason=reason,
                                 created_at=now - timedelta(days=rng.randint(0, 12), hours=rng.randint(0, 8))))

    # campanha encerrada: 10 boxes, 12 comprovantes cada
    closed_batches = distribute(closed, "MAES", 1, rng.sample(active_occs, 10), 12, datetime(2026, 4, 18))
    cpool = [v for b, vs in closed_batches for v in vs[: rng.randint(4, 9)]]
    rng.shuffle(cpool)
    for v in cpool:
        when = datetime(2026, 4, 21) + timedelta(days=rng.randint(0, 20), hours=rng.randint(8, 17), minutes=rng.randint(0, 59))
        participate(closed, v, rng.choice(people), when, rng.choice(attendants))
    for b, _ in closed_batches:
        b.status = "CONCLUIDO"
    db.commit()

    # ---------------------------------------------------------------- apuração da campanha encerrada (regras reais do sistema)
    from app.services import draw_service
    draw_service.freeze_base(db, closed.id, admin.id, "admin")
    n = closed.lucky_number_seq
    prizes = closed.prizes
    # Extrações FICTÍCIAS, escolhidas para que o número apurado exista na base (correspondência exata)
    t1 = f"{min(37, n):05d}"
    ext1 = [f"{rng.randint(1000, 9999)}{d}" for d in t1]
    r1 = draw_service.execute_federal_lottery_draw(db, closed.id, "6061", datetime(2026, 5, 16, 22), ext1, None, admin.id, "admin",
                                                   prize_id=prizes[0].id)
    ext2 = [f"{rng.randint(1000, 9999)}{d}" for d in "8" + "".join(str(rng.randint(0, 9)) for _ in range(4))]
    r2 = draw_service.execute_federal_lottery_draw(db, closed.id, "6061", datetime(2026, 5, 16, 22), ext2, None, admin.id, "admin",
                                                   prize_id=prizes[1].id)
    draw_service.update_delivery(db, r1["id"], "CONTATADO", "Contato por telefone; dados do contemplado confirmados.", admin.id, "admin")
    draw_service.update_delivery(db, r1["id"], "ENTREGUE", "Entrega no Complexo com termo de recebimento assinado.", admin.id, "admin")
    draw_service.update_delivery(db, r2["id"], "CONTATADO", "Mensagem enviada; aguardando comparecimento.", admin.id, "admin")
    db.commit()
