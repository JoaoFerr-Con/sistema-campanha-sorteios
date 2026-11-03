"""Regras de negócio e segurança introduzidas na versão 2."""
from datetime import datetime, timedelta
from app.core.security import create_access_token
from app.models.entities import Campaign, Box, BoxOccupancy, Permissionario, User, Voucher
from app.services.draw_service import pick_winner, concentration, parse_extraction, target_from_extraction
from app.services.attendance_service import is_valid_cpf


def auth(user_id=1, username="admin", role="ADMIN", perm_id=None, tv=0):
    return {"Authorization": f"Bearer {create_access_token(user_id, username, role, perm_id, tv)}"}


ADMIN = auth()
ATT = auth(2, "atendente", "ATENDENTE")


# ---------------------------------------------------------------- segurança

def test_data_endpoints_require_authentication(client):
    for path in ["/api/v1/campaigns", "/api/v1/boxes", "/api/v1/permissionarios", "/api/v1/vouchers/lookup/NATAL-00001",
                 "/api/v1/reports/kpis", "/api/v1/draw/results/1", "/api/v1/boxes/map"]:
        assert client.get(path).status_code == 401, path


def test_role_comes_from_database_not_token(client):
    # Token forjado dizendo que o atendente é ADMIN: o perfil do banco prevalece.
    forged = auth(2, "atendente", "ADMIN")
    assert client.get("/api/v1/reports/audit-trail", headers=forged).status_code == 403


def test_logout_invalidates_token(client, test_db):
    assert client.post("/api/v1/users", headers=ADMIN, json={"username": "operador_logout", "password": "senhaforte1",
                                                             "full_name": "Operador Teste", "role": "ATENDENTE"}).status_code == 200
    res = client.post("/api/v1/auth/login", json={"username": "operador_logout", "password": "senhaforte1"})
    token = {"Authorization": f"Bearer {res.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=token).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=token).status_code == 200
    assert client.get("/api/v1/auth/me", headers=token).status_code == 401


def test_login_rate_limit(client):
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"username": "ninguem", "password": "x"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "ninguem", "password": "x"}).status_code == 429


def test_system_info_is_public_and_flags_demo(client):
    info = client.get("/api/v1/system/info").json()
    assert info["demo_mode"] is True
    assert any(a["username"] == "admin" for a in info["demo_accounts"])


def test_attempts_mask_cpf(client):
    rows = client.get("/api/v1/attendance/attempts", headers=ATT).json()
    assert isinstance(rows, list) and rows
    assert all(r["participant_cpf"] in ("—",) or r["participant_cpf"].startswith("***") for r in rows)


# ---------------------------------------------------------------- campanha

def _new_campaign(client, **extra):
    now = datetime.utcnow()
    body = {"name": "Campanha Regras", "description": "Teste", "legal_promoter_name": "Prefeitura",
            "legal_promoter_doc": "05.105.200/0001-22", "start_date": (now - timedelta(days=1)).isoformat(),
            "end_date": (now + timedelta(days=30)).isoformat(), "purchase_start_date": (now - timedelta(days=1)).isoformat(),
            "purchase_end_date": (now + timedelta(days=20)).isoformat(),
            "registration_end_date": (now + timedelta(days=25)).isoformat(),
            "draw_approximation_rule": "SOMENTE_EXATO", "regulation_reference": "Proc. 1/2026",
            "prizes": [{"title": "Bicicleta"}]}
    body.update(extra)
    return client.post("/api/v1/campaigns", headers=ADMIN, json=body)


def test_purchase_period_must_be_inside_campaign(client):
    now = datetime.utcnow()
    res = _new_campaign(client, purchase_end_date=(now + timedelta(days=40)).isoformat())
    assert res.status_code == 400
    assert "dentro do período" in res.json()["detail"]


def test_legal_approval_requires_submission_and_readiness(client):
    cid = _new_campaign(client).json()["campaign_id"]
    legal = {"legal_promoter_name": "P", "legal_promoter_doc": "D", "justification": "Parecer 1/2026",
             **{k: True for k in ["legal_promoter_ok", "participant_compliance_ok", "prizes_funded_ok",
                                  "rules_approved_ok", "lgpd_declared_ok", "electoral_cleared_ok"]}}
    assert client.post(f"/api/v1/campaigns/{cid}/legal-approvals", headers=ADMIN, json=legal).status_code == 400
    assert client.post(f"/api/v1/campaigns/{cid}/transition", headers=ADMIN,
                       json={"target_status": "AGUARDANDO_APROVACAO"}).status_code == 200
    # Em aprovação, a campanha não é mais editável
    assert client.put(f"/api/v1/campaigns/{cid}", headers=ADMIN, json={"name": "Outro nome"}).status_code == 400
    assert client.post(f"/api/v1/campaigns/{cid}/legal-approvals", headers=ADMIN, json=legal).json()["campaign_status"] == "APROVADA"
    detail = client.get(f"/api/v1/campaigns/{cid}", headers=ADMIN).json()
    assert {s["key"]: s["done"] for s in detail["readiness"]}["juridico"] is True
    # Devolver para elaboração exige justificativa e zera a aprovação
    assert client.post(f"/api/v1/campaigns/{cid}/transition", headers=ADMIN,
                       json={"target_status": "EM_ELABORACAO"}).status_code == 400
    assert client.post(f"/api/v1/campaigns/{cid}/transition", headers=ADMIN,
                       json={"target_status": "EM_ELABORACAO", "justification": "Ajuste no regulamento"}).status_code == 200
    detail = client.get(f"/api/v1/campaigns/{cid}", headers=ADMIN).json()
    assert not any(detail["legal_checklist"].values())


# ---------------------------------------------------------------- talões

_ACTIVE = {}


def _pilot(test_db):
    """Campanha ativa própria destes testes (a piloto é encerrada pelo teste de apuração)."""
    from tests.conftest import TestClient  # noqa
    if "c" not in _ACTIVE:
        now = datetime.utcnow()
        from app.models.entities import CampaignPrize, VoucherBatch
        import json as _j
        c = Campaign(name="Campanha V2", description="x", start_date=now - timedelta(days=1), end_date=now + timedelta(days=30),
                     purchase_start_date=now - timedelta(days=1), purchase_end_date=now + timedelta(days=20),
                     registration_end_date=now + timedelta(days=25), status="ATIVA", draw_approximation_rule="SOMENTE_EXATO",
                     regulation_reference="R", legal_promoter_name="P", legal_promoter_doc="D",
                     legal_checklist_json=_j.dumps({}), min_purchase_value=20, max_numbers_per_cpf=50)
        test_db.add(c)
        test_db.flush()
        box = test_db.query(Box).filter(Box.box_number == "260").first()
        occ = test_db.query(BoxOccupancy).filter(BoxOccupancy.box_id == box.id, BoxOccupancy.is_current == True).first()
        b = VoucherBatch(campaign_id=c.id, permissionario_id=occ.permissionario_id, box_id=box.id, batch_number=1,
                         code_prefix="VDOIS", start_number=1, end_number=50, total_vouchers=50)
        test_db.add(b)
        test_db.flush()
        for n in range(1, 51):
            test_db.add(Voucher(batch_id=b.id, campaign_id=c.id, box_id=box.id, permissionario_id=occ.permissionario_id,
                                full_code=f"VDOIS-{n:05d}", sequence_number=n))
        test_db.commit()
        _ACTIVE["c"] = c.id
    c = test_db.query(Campaign).get(_ACTIVE["c"])
    box = test_db.query(Box).filter(Box.box_number == "260").first()
    occ = test_db.query(BoxOccupancy).filter(BoxOccupancy.box_id == box.id, BoxOccupancy.is_current == True).first()
    return c, box, occ


def test_batch_prefix_and_cross_campaign_overlap(client, test_db):
    c, box, occ = _pilot(test_db)
    base = {"campaign_id": c.id, "box_id": box.id, "permissionario_id": occ.permissionario_id}
    bad = client.post("/api/v1/vouchers/batches", headers=ADMIN, json={**base, "code_prefix": "NA TAL", "start_number": 1, "end_number": 2})
    assert bad.status_code == 422 or bad.status_code == 400
    big = client.post("/api/v1/vouchers/batches", headers=ADMIN, json={**base, "code_prefix": "BIG", "start_number": 1, "end_number": 9000})
    assert big.status_code == 400


def test_cancel_batch_preserves_used(client, test_db):
    c, box, occ = _pilot(test_db)
    res = client.post("/api/v1/vouchers/batches", headers=ADMIN, json={
        "campaign_id": c.id, "box_id": box.id, "permissionario_id": occ.permissionario_id,
        "code_prefix": "CANC", "start_number": 1, "end_number": 5})
    bid = res.json()["batch_id"]
    assert client.post(f"/api/v1/vouchers/batches/{bid}/cancel", headers=ADMIN, json={"reason": "curto"}).status_code == 422
    out = client.post(f"/api/v1/vouchers/batches/{bid}/cancel", headers=ADMIN, json={"reason": "Talão danificado na gráfica"})
    assert out.json()["vouchers_cancelled"] == 5
    elig = client.get("/api/v1/vouchers/eligibility", headers=ATT, params={"campaign_id": c.id, "code": "canc 3"}).json()
    assert elig["ok"] is False and elig["kind"] == "CANCELADO"


# ---------------------------------------------------------------- balcão

def test_cpf_check_digits():
    assert is_valid_cpf("52998224725")
    assert not is_valid_cpf("11111111111")
    assert not is_valid_cpf("52998224726")


def test_counter_rejects_invalid_cpf_and_irregular_permissionario(client, test_db):
    c, box, occ = _pilot(test_db)
    payload = {"campaign_id": c.id, "voucher_code": "VDOIS-00010", "participant_cpf": "111.111.111-11",
               "participant_name": "Fulano de Tal", "participant_phone": "91988887777"}
    assert client.post("/api/v1/attendance/validate", headers=ATT, json=payload).status_code == 422

    perm = test_db.query(Permissionario).get(occ.permissionario_id)
    client.patch(f"/api/v1/permissionarios/{perm.id}", headers=ADMIN, json={"status": "SUSPENSO", "justification": "Teste de bloqueio"})
    payload["participant_cpf"] = "390.533.447-05"
    res = client.post("/api/v1/attendance/validate", headers=ATT, json=payload)
    assert res.status_code == 422 and "irregular" in res.json()["detail"]
    client.patch(f"/api/v1/permissionarios/{perm.id}", headers=ADMIN, json={"status": "ATIVO", "justification": "Regularizado"})
    res = client.post("/api/v1/attendance/validate", headers=ATT, json=payload)
    assert res.status_code == 200
    assert res.json()["participant"]["cpf_masked"].startswith("***")


def test_lucky_numbers_are_sequential_and_unique(client, test_db):
    c, _, _ = _pilot(test_db)
    numbers = []
    for i, cpf in enumerate(["12345678909", "11144477735"]):
        res = client.post("/api/v1/attendance/validate", headers=ATT, json={
            "campaign_id": c.id, "voucher_code": f"VDOIS-{20 + i:05d}", "participant_cpf": cpf,
            "participant_name": "Participante Teste", "participant_phone": "91988887777"})
        assert res.status_code == 200, res.text
        numbers.append(int(res.json()["lucky_number"]))
    assert numbers[1] == numbers[0] + 1


def test_portal_min_value(client, test_db):
    perm = test_db.query(Permissionario).filter(Permissionario.name == "Sulamita Ferreira Figueira").first()
    user = test_db.query(User).filter(User.username == "permissionario_260").first()
    _pilot(test_db)
    h = auth(user.id, user.username, "PERMISSIONARIO", perm.id)
    res = client.post("/api/v1/portal/issue-voucher", headers=h, json={"voucher_code": "VDOIS-00030", "issued_value": 5})
    assert res.status_code == 400 and "mínimo" in res.json()["detail"]


# ---------------------------------------------------------------- apuração (unidade)

def test_extraction_parsing_keeps_leading_zeros():
    clean = parse_extraction(["24.568", "13492", "56 701", "89234", "07.810"])
    assert target_from_extraction(clean) == "82140"


def test_extraction_requires_five_digits():
    import pytest
    from app.core.exceptions import DomainRuleException
    with pytest.raises(DomainRuleException):
        parse_extraction(["1234", "13492", "56701", "89234", "07815"])


def test_pick_winner_rules():
    nums = [1, 2, 3, 10, 20]
    assert pick_winner(nums, 3, "SOMENTE_EXATO") == (3, "EXATO", 0)
    assert pick_winner(nums, 4, "SOMENTE_EXATO")[0] is None
    assert pick_winner(nums, 4, "SUPERIOR_DEPOIS_INFERIOR") == (10, "APROXIMADO", 6)
    assert pick_winner(nums, 50, "SUPERIOR_DEPOIS_INFERIOR") == (20, "APROXIMADO", 30)
    assert pick_winner(nums, 15, "MAIS_PROXIMO") == (20, "APROXIMADO", 5)  # empate -> superior
    assert pick_winner(nums, 14, "MAIS_PROXIMO") == (10, "APROXIMADO", 4)


def test_concentration_detects_sequential_bias():
    seq = list(range(1, 501))
    c = concentration(seq, "MAIS_PROXIMO")
    assert c["top_number"] == "00500" and c["top_share_pct"] > 99
    assert c["is_concentrated"] is True
    exact = concentration(seq, "SOMENTE_EXATO")
    assert exact["top_share_pct"] == 0.001 and exact["no_winner_pct"] == 99.5


def test_draw_annul_redo_minutes_and_exports(client, test_db):
    """Depende do teste de apuração da fase 8 (campanha piloto já apurada)."""
    c = test_db.query(Campaign).filter(Campaign.name.like("Campanha Piloto%")).first()
    ov = client.get(f"/api/v1/draw/overview/{c.id}", headers=ADMIN).json()
    assert ov["integrity"]["intact"] is True
    assert ov["concentration"]["is_concentrated"] in (True, False)
    first = ov["results"][0]
    prize_id = first["prize_id"]
    body = {"campaign_id": c.id, "contest_number": "5901", "draw_date": datetime.utcnow().isoformat(),
            "extraction_prizes": ["00001", "00000", "00000", "00000", "00002"], "prize_id": prize_id}
    assert client.post("/api/v1/draw/execute-federal", headers=ADMIN, json=body).status_code == 409  # já apurado
    assert client.post(f"/api/v1/draw/{first['id']}/annul", headers=ADMIN, json={"reason": "curta"}).status_code == 422
    assert client.post(f"/api/v1/draw/{first['id']}/annul", headers=ADMIN,
                       json={"reason": "Extração digitada errada — Ofício 12/2026 da comissão"}).status_code == 200
    redo = client.post("/api/v1/draw/execute-federal", headers=ADMIN, json=body)
    assert redo.status_code == 200 and redo.json()["target_number"] == "10002"
    d = client.post(f"/api/v1/draw/{redo.json()['id']}/delivery", headers=ADMIN,
                    json={"delivery_status": "CONTATADO", "delivery_notes": "Ligação em 03/11"})
    assert d.status_code == 200
    minutes = client.get(f"/api/v1/draw/minutes/{c.id}", headers=ADMIN)
    assert minutes.status_code == 200 and "Ata de apuração" in minutes.text and "ANULADO" in minutes.text
    base = client.get(f"/api/v1/draw/base/{c.id}.csv", headers=ADMIN)
    import hashlib
    assert hashlib.sha256(base.content).hexdigest() == ov["integrity"]["snapshot"]["sha256"]
    for name in ["participacoes", "lotes", "permissionarios", "ocorrencias", "auditoria"]:
        for fmt in ["csv", "xlsx"]:
            r = client.get(f"/api/v1/reports/export/{name}.{fmt}", headers=ADMIN, params={"campaign_id": c.id})
            assert r.status_code == 200, (name, fmt, r.text[:200])
    audit = client.get("/api/v1/reports/audit-trail", headers=ADMIN, params={"paged": True, "action": "DRAW_ANNULLED"}).json()
    assert audit["total"] == 1


def test_box_map_has_368_positions(client):
    m = client.get("/api/v1/boxes/map", headers=ADMIN).json()
    assert len(m) == 368 and m[259]["box_number"] == "260" and m[259]["status"] == "CONFIRMADO"
