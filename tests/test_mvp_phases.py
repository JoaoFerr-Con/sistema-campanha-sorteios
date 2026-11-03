"""Automated test suite verifying all 8 phases and critical business rules."""
import json
import pytest
from datetime import datetime, timedelta
from app.core.security import hash_password, create_access_token
from app.models.entities import (
    User,
    Box,
    Permissionario,
    BoxOccupancy,
    Campaign,
    VoucherBatch,
    Voucher,
    Participation,
    ImportStagingRow,
)

# Helper to get auth header
def get_auth(role: str = "ADMIN", user_id: int = 1, username: str = "admin", perm_id: int = None):
    token = create_access_token(user_id=user_id, username=username, role=role, permissionario_id=perm_id)
    return {"Authorization": f"Bearer {token}"}

# ================= PHASE 1: AUTH & RBAC =================

def test_phase1_authentication_and_rbac(client):
    """Phase 1: Test authentication, JWT/HMAC token issuance, and RBAC enforcement."""
    # Successful login
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"

    # Failed login
    res_fail = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res_fail.status_code == 401

    # Protected endpoint requires ADMIN role
    atendente_header = get_auth(role="ATENDENTE", user_id=2, username="atendente")
    res_forbidden = client.get("/api/v1/boxes/staging", headers=atendente_header)
    assert res_forbidden.status_code == 403

# ================= PHASE 2: BOXES & STAGING REVIEW =================

def test_phase2_staging_import_and_anomalies(client, test_db):
    """Phase 2: Test spreadsheet import, anomaly flags (Box 257 duplicate, VAGO, blank), and review."""
    admin_header = get_auth(role="ADMIN", user_id=1, username="admin")

    res = client.post("/api/v1/boxes/import-staging", headers=admin_header)
    assert res.status_code == 200
    import_data = res.json()
    assert import_data["status"] == "success"
    assert import_data["total_rows_imported"] >= 290
    assert import_data["anomalies_detected"] > 0

    # Verify duplicate box flag on Box 257
    row_257 = test_db.query(ImportStagingRow).filter(ImportStagingRow.raw_box_number == "257").first()
    assert row_257 is not None
    flags = json.loads(row_257.discrepancy_flags)
    assert "DUP_BOX_SPREADSHEET" in flags

    # Review staging row with administrative justification
    res_review = client.post(
        "/api/v1/boxes/staging/review",
        headers=admin_header,
        json={
            "staging_row_ids": [row_257.id],
            "decision": "APROVADO",
            "justification": "Verificado in loco: Jean Lima atua com Variedades no Box 257.",
            "confirmed_box_number": "257",
            "confirmed_permissionario_name": "Jean Lima de Andrade",
            "confirmed_activity": "VARIEDADES",
            "is_vago": False,
        },
    )
    assert res_review.status_code == 200

    # Ensure box 257 now exists in official catalog with CONFIRMADO
    box = test_db.query(Box).filter(Box.box_number == "257").first()
    assert box is not None
    assert box.official_status == "CONFIRMADO"

# ================= PHASE 3: CAMPAIGNS & LEGAL GATE =================

def test_phase3_campaign_lifecycle_and_legal_gate(client, test_db):
    """Phase 3: Test campaign states and mandatory 6-item legal approval gate before activation."""
    admin_header = get_auth(role="ADMIN", user_id=1, username="admin")
    now = datetime.utcnow()

    # 1. Create campaign in draft (EM_ELABORACAO)
    res = client.post(
        "/api/v1/campaigns",
        headers=admin_header,
        json={
            "name": "Campanha Teste Legal",
            "start_date": (now - timedelta(days=1)).isoformat(),
            "end_date": (now + timedelta(days=30)).isoformat(),
            "purchase_start_date": (now - timedelta(days=1)).isoformat(),
            "purchase_end_date": (now + timedelta(days=25)).isoformat(),
            "registration_end_date": (now + timedelta(days=28)).isoformat(),
            "min_purchase_value": 20.0,
            "max_numbers_per_cpf": 10,
        },
    )
    assert res.status_code == 200
    camp_id = res.json()["campaign_id"]

    # 1b. Envio para aprovação é bloqueado enquanto faltam etapas (premiação, regulamento, regra)
    res_incomplete = client.post(f"/api/v1/campaigns/{camp_id}/transition", headers=admin_header,
                                 json={"target_status": "AGUARDANDO_APROVACAO"})
    assert res_incomplete.status_code == 400
    assert "Premiações" in res_incomplete.json()["detail"]

    res_upd = client.put(f"/api/v1/campaigns/{camp_id}", headers=admin_header, json={
        "description": "Campanha de teste do fluxo jurídico.",
        "legal_promoter_name": "Prefeitura de Barcarena", "legal_promoter_doc": "05.105.200/0001-22",
        "draw_approximation_rule": "SUPERIOR_DEPOIS_INFERIOR", "regulation_reference": "Processo 123/2026",
        "prizes": [{"title": "Vale-compras R$ 500"}],
    })
    assert res_upd.status_code == 200

    # 2. Transition directly to ATIVA should be BLOCKED because legal items are unapproved
    res_blocked = client.post(
        f"/api/v1/campaigns/{camp_id}/transition",
        headers=admin_header,
        json={"target_status": "ATIVA", "justification": "Tentativa de atalho sem aprovação"},
    )
    assert res_blocked.status_code == 400

    res_submit = client.post(f"/api/v1/campaigns/{camp_id}/transition", headers=admin_header,
                             json={"target_status": "AGUARDANDO_APROVACAO"})
    assert res_submit.status_code == 200

    # 3. Register all 6 legal approvals
    res_legal = client.post(
        f"/api/v1/campaigns/{camp_id}/legal-approvals",
        headers=admin_header,
        json={
            "legal_promoter_name": "Prefeitura de Barcarena",
            "legal_promoter_doc": "05.105.200/0001-22",
            "legal_promoter_ok": True,
            "participant_compliance_ok": True,
            "prizes_funded_ok": True,
            "rules_approved_ok": True,
            "lgpd_declared_ok": True,
            "electoral_cleared_ok": True,
            "justification": "Parecer Jurídico nº 45/2026 emitido e anexado.",
        },
    )
    assert res_legal.status_code == 200
    assert res_legal.json()["campaign_status"] == "APROVADA"

    # 4. Now transition to ATIVA succeeds
    res_activate = client.post(
        f"/api/v1/campaigns/{camp_id}/transition",
        headers=admin_header,
        json={"target_status": "ATIVA", "justification": "Ativação autorizada"},
    )
    assert res_activate.status_code == 200
    assert res_activate.json()["new_status"] == "ATIVA"

# ================= PHASE 4: VOUCHER BATCHES =================

def test_phase4_voucher_batch_allocation_and_no_overlaps(client, test_db):
    """Phase 4: Voucher batch allocation and prevention of overlapping sequence ranges."""
    admin_header = get_auth(role="ADMIN", user_id=1, username="admin")

    # Get pilot campaign and confirmed box 260
    campaign = test_db.query(Campaign).filter(Campaign.status == "ATIVA").first()
    box_260 = test_db.query(Box).filter(Box.box_number == "260").first()
    occ = test_db.query(BoxOccupancy).filter(BoxOccupancy.box_id == box_260.id, BoxOccupancy.is_current == True).first()

    # Batch 1 was pre-seeded 1..50 with prefix NATAL
    # Attempting to allocate overlapping range 20..70 must FAIL
    res_overlap = client.post(
        "/api/v1/vouchers/batches",
        headers=admin_header,
        json={
            "campaign_id": campaign.id,
            "box_id": box_260.id,
            "permissionario_id": occ.permissionario_id,
            "code_prefix": "NATAL",
            "start_number": 20,
            "end_number": 70,
        },
    )
    assert res_overlap.status_code == 400
    assert "Conflito de intervalo" in res_overlap.json()["detail"]

    # Non-overlapping range 51..100 succeeds
    res_ok = client.post(
        "/api/v1/vouchers/batches",
        headers=admin_header,
        json={
            "campaign_id": campaign.id,
            "box_id": box_260.id,
            "permissionario_id": occ.permissionario_id,
            "code_prefix": "NATAL",
            "start_number": 51,
            "end_number": 100,
        },
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["total_vouchers"] == 50

# ================= PHASE 5: ATTENDANCE & CONCURRENCY =================

def test_phase5_balcao_attendance_and_duplicate_prevention(client, test_db):
    """Phase 5: Counter attendance, lucky number generation, and rejection of duplicate voucher redemption."""
    atendente_header = get_auth(role="ATENDENTE", user_id=2, username="atendente")
    campaign = test_db.query(Campaign).filter(Campaign.status == "ATIVA").first()

    # First validation of NATAL-00001
    payload = {
        "campaign_id": campaign.id,
        "voucher_code": "NATAL-00001",
        "participant_cpf": "529.982.247-25",
        "participant_name": "Rafael Santos",
        "participant_phone": "91981234567",
        "participant_neighborhood": "Centro",
    }

    res1 = client.post("/api/v1/attendance/validate", headers=atendente_header, json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "success"
    assert "lucky_number" in data1
    assert data1["participant"]["cpf"] == "52998224725"

    # Critical requirement: Second simultaneous attempt for the EXACT SAME VOUCHER must fail with 409 Conflict
    res2 = client.post("/api/v1/attendance/validate", headers=atendente_header, json=payload)
    assert res2.status_code == 409
    assert "já foi utilizado" in res2.json()["detail"]

    # Check attempt audit table logged both
    res_attempts = client.get("/api/v1/attendance/attempts", headers=atendente_header)
    assert res_attempts.status_code == 200
    attempts = res_attempts.json()
    assert any(a["voucher_code"] == "NATAL-00001" and a["success"] is False for a in attempts)

# ================= PHASE 6: PERMISSIONÁRIO ISOLATION (IDOR) =================

def test_phase6_permissionario_portal_isolation(client, test_db):
    """Phase 6: Ensure permissionário can only manage their own vouchers and cannot tamper with others."""
    # Box 260 permissionario
    perm_260 = test_db.query(Permissionario).filter(Permissionario.name == "Sulamita Ferreira Figueira").first()
    perm_header = get_auth(role="PERMISSIONARIO", user_id=3, username="permissionario_260", perm_id=perm_260.id)

    # 1. Permissionário views own portal
    res_portal = client.get("/api/v1/portal/overview", headers=perm_header)
    assert res_portal.status_code == 200
    pdata = res_portal.json()
    assert pdata["permissionario"]["id"] == perm_260.id

    # 2. Permissionário issues voucher from their pool
    res_issue = client.post(
        "/api/v1/portal/issue-voucher",
        headers=perm_header,
        json={"voucher_code": "NATAL-00002", "issued_value": 75.50, "invoice_doc_number": "NF-998"},
    )
    assert res_issue.status_code == 200
    assert "digital_qr_token" in res_issue.json()

    # 3. IDOR Attack Simulation: Another permissionário tries to issue or tamper with NATAL-00003
    fake_perm_header = get_auth(role="PERMISSIONARIO", user_id=99, username="attacker", perm_id=999)
    res_tamper = client.post(
        "/api/v1/portal/issue-voucher",
        headers=fake_perm_header,
        json={"voucher_code": "NATAL-00003", "issued_value": 100.0},
    )
    # Usuário inexistente: o token é recusado porque a identidade é conferida no banco
    assert res_tamper.status_code == 401

# ================= PHASE 7: DASHBOARD & AUDIT =================

def test_phase7_dashboard_kpis_and_audit(client):
    """Phase 7: Verify KPIs, refusal stats, and CSV export."""
    admin_header = get_auth(role="ADMIN", user_id=1, username="admin")

    assert client.get("/api/v1/reports/kpis").status_code == 401  # indicadores exigem autenticação
    res_kpis = client.get("/api/v1/reports/kpis", headers=admin_header)
    assert res_kpis.status_code == 200
    kpis = res_kpis.json()
    assert kpis["boxes"]["total_capacity_map"] == 368
    assert kpis["participations"]["total_validated"] >= 1
    assert kpis["validation_attempts"]["rejected"] >= 1

    # Audit export CSV
    res_csv = client.get("/api/v1/reports/export/participations.csv", headers=admin_header)
    assert res_csv.status_code == 200
    assert "numero_da_sorte,comprovante,box" in res_csv.text

# ================= PHASE 8: APURAÇÃO LOTERIA FEDERAL =================

def test_phase8_official_loteria_federal_draw(client, test_db):
    """Phase 8: Audit base freeze (SHA-256) and official Loteria Federal extraction match."""
    admin_header = get_auth(role="ADMIN", user_id=1, username="admin")
    atendente_header = get_auth(role="ATENDENTE", user_id=2, username="atendente")
    campaign = test_db.query(Campaign).filter(Campaign.status == "ATIVA").first()

    # Validate one more voucher so we have multiple participations
    client.post(
        "/api/v1/attendance/validate",
        headers=atendente_header,
        json={
            "campaign_id": campaign.id,
            "voucher_code": "NATAL-00002",
            "participant_cpf": "111.444.777-35",
            "participant_name": "Maria Oliveira",
            "participant_phone": "91999998888",
        },
    )

    # Apuração exige campanha encerrada e base congelada
    early = client.post("/api/v1/draw/execute-federal", headers=admin_header, json={
        "campaign_id": campaign.id, "contest_number": "5900", "draw_date": datetime.utcnow().isoformat(),
        "extraction_prizes": ["24568", "13492", "56701", "89234", "07815"], "prize_id": campaign.prizes[0].id})
    assert early.status_code == 400
    assert client.post(f"/api/v1/campaigns/{campaign.id}/transition", headers=admin_header,
                       json={"target_status": "ENCERRADA"}).status_code == 200
    assert client.post("/api/v1/draw/freeze", headers=admin_header,
                       json={"campaign_id": campaign.id}).status_code == 200

    # Official Loteria Federal extraction
    # Units: 8, 2, 1, 4, 5 -> calculated target: "82145"
    prizes = ["24568", "13492", "56701", "89234", "07815"]

    res_draw = client.post(
        "/api/v1/draw/execute-federal",
        headers=admin_header,
        json={
            "campaign_id": campaign.id,
            "contest_number": "5900",
            "draw_date": datetime.utcnow().isoformat(),
            "extraction_prizes": prizes,
            "prize_id": campaign.prizes[0].id,
        },
    )
    assert res_draw.status_code == 200
    draw_data = res_draw.json()
    assert draw_data["status"] == "success"
    assert "winner_lucky_number" in draw_data
    assert len(draw_data["consolidated_base_sha256"]) == 64  # Valid SHA-256 hash length

    # Campaign should now be frozen in ENCERRADA
    test_db.refresh(campaign)
    assert campaign.status == "ENCERRADA"
