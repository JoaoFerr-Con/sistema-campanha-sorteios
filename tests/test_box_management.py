"""Cadastro manual de permissionários, troca de titular e edição de boxes."""
from app.core.security import create_access_token
from app.models.entities import Box, BoxOccupancy, Permissionario, Campaign, VoucherBatch, Voucher

ADMIN = {"Authorization": f"Bearer {create_access_token(1, 'admin', 'ADMIN', None, 0)}"}


def test_create_permissionario_with_box(client, test_db):
    r = client.post("/api/v1/permissionarios", headers=ADMIN, json={
        "name": "Benedita Pantoja dos Santos.", "document_cpf_cnpj": "529.982.247-25", "phone": "(91) 98888-7777",
        "box_number": "12", "activity_name": "artesanato", "authorization_term_ref": "TERMO-2026-012",
        "justification": "Termo de permissão 012/2026 assinado"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Benedita Pantoja dos Santos"
    d = client.get("/api/v1/boxes/12/detail", headers=ADMIN).json()
    assert d["status"] == "CONFIRMADO" and d["current"]["permissionario"] == "Benedita Pantoja dos Santos"
    assert d["current"]["activity"] == "ARTESANATO"
    assert d["history"][0]["action"] == "BOX_HOLDER_ASSIGNED"
    # duplicidade por nome e por documento
    assert client.post("/api/v1/permissionarios", headers=ADMIN, json={"name": "Benedita Pantoja dos Santos",
                                                                       "justification": "teste dup"}).status_code == 409
    assert client.post("/api/v1/permissionarios", headers=ADMIN, json={"name": "Outra Pessoa", "document_cpf_cnpj": "52998224725",
                                                                       "justification": "teste dup"}).status_code == 409


def test_box_number_must_be_on_map(client):
    r = client.post("/api/v1/permissionarios", headers=ADMIN, json={"name": "Fora do Mapa", "box_number": "999",
                                                                    "activity_name": "X", "justification": "teste"})
    assert r.status_code == 400 and "368" in r.json()["detail"]


def test_transfer_keeps_history_and_requires_ack_for_open_vouchers(client, test_db):
    old = test_db.query(Permissionario).filter(Permissionario.name == "Sulamita Ferreira Figueira").first()
    new = client.post("/api/v1/permissionarios", headers=ADMIN, json={"name": "Novo Titular Duzentos e Sessenta",
                                                                      "justification": "Cadastro para transferência"}).json()
    body = {"permissionario_id": new["id"], "justification": "Cessão do box — processo 77/2026"}
    # a titular atual tem comprovantes não utilizados em campanha em andamento
    has_open = test_db.query(Voucher).join(Campaign).filter(
        Voucher.permissionario_id == old.id, Voucher.status.in_(["DISTRIBUIDO", "EMITIDO"]),
        Campaign.status.in_(["APROVADA", "ATIVA"])).count()
    r = client.post("/api/v1/boxes/260/holder", headers=ADMIN, json=body)
    if has_open:
        assert r.status_code == 409 and "comprovante" in r.json()["detail"]
        r = client.post("/api/v1/boxes/260/holder", headers=ADMIN, json={**body, "acknowledge_outstanding": True})
    assert r.status_code == 200, r.text
    d = client.get("/api/v1/boxes/260/detail", headers=ADMIN).json()
    assert d["current"]["permissionario"] == "Novo Titular Duzentos e Sessenta"
    assert d["current"]["activity"] == "SALÃO E BARBEARIA"  # herdada quando não informada
    previous = [h for h in d["holders"] if not h["is_current"]]
    assert previous and previous[0]["permissionario"] == "Sulamita Ferreira Figueira" and previous[0]["end_date"]
    assert d["history"][0]["action"] == "BOX_HOLDER_TRANSFERRED"
    # devolve para a titular original, para não afetar outros testes
    r = client.post("/api/v1/boxes/260/holder", headers=ADMIN, json={"permissionario_id": old.id, "justification": "Retorno",
                                                                     "acknowledge_outstanding": True})
    assert r.status_code == 200


def test_release_and_update_box_rules(client, test_db):
    client.post("/api/v1/permissionarios", headers=ADMIN, json={"name": "Titular Box Trinta", "box_number": "30",
                                                                "activity_name": "PEIXES", "justification": "Termo 30"})
    # não pode marcar vago com titular vigente
    r = client.patch("/api/v1/boxes/30", headers=ADMIN, json={"official_status": "VAGO_CONFIRMADO", "justification": "teste"})
    assert r.status_code == 400 and "Encerrar vínculo" in r.json()["detail"]
    # muda a atividade
    assert client.patch("/api/v1/boxes/30", headers=ADMIN, json={"activity_name": "camarão e marisco",
                                                                 "justification": "Mudança de ramo"}).status_code == 200
    assert client.get("/api/v1/boxes/30/detail", headers=ADMIN).json()["current"]["activity"] == "CAMARÃO E MARISCO"
    # encerra o vínculo
    r = client.post("/api/v1/boxes/30/release", headers=ADMIN, json={"target_status": "VAGO_CONFIRMADO",
                                                                     "justification": "Desistência formalizada"})
    assert r.status_code == 200 and r.json()["official_status"] == "VAGO_CONFIRMADO"
    d = client.get("/api/v1/boxes/30/detail", headers=ADMIN).json()
    assert d["current"] is None and d["holders"][0]["end_date"]
    # sem titular, não pode confirmar
    r = client.patch("/api/v1/boxes/30", headers=ADMIN, json={"official_status": "CONFIRMADO", "justification": "teste"})
    assert r.status_code == 400
    # sem uso bloqueia novo vínculo até mudar a situação
    client.patch("/api/v1/boxes/30", headers=ADMIN, json={"official_status": "SEM_USO", "justification": "Interditado"})
    p = test_db.query(Permissionario).filter(Permissionario.name == "Titular Box Trinta").first()
    r = client.post("/api/v1/boxes/30/holder", headers=ADMIN, json={"permissionario_id": p.id, "justification": "Retorno"})
    assert r.status_code == 400 and "sem uso" in r.json()["detail"]


def test_new_holder_of_confirmed_box_can_receive_batch(client, test_db):
    c = test_db.query(Campaign).filter(Campaign.status.in_(["ATIVA", "APROVADA"])).first()
    if not c:
        return
    r = client.post("/api/v1/permissionarios", headers=ADMIN, json={"name": "Titular Com Talao", "box_number": "77",
                                                                    "activity_name": "MERCEARIA", "justification": "Termo 77"})
    pid = r.json()["id"]
    box = test_db.query(Box).filter(Box.box_number == "77").first()
    res = client.post("/api/v1/vouchers/batches", headers=ADMIN, json={"campaign_id": c.id, "box_id": box.id, "permissionario_id": pid,
                                                                       "code_prefix": "SETE", "start_number": 1, "end_number": 3})
    assert res.status_code == 200, res.text


def test_activities_endpoint(client):
    acts = client.get("/api/v1/activities", headers=ADMIN).json()
    assert "ARTESANATO" in acts
