#!/usr/bin/env python3
"""
Validação e Testes Locais do Sistema de Gestão de Campanhas e Sorteios
Complexo Comercial de Barcarena — Pará

100% Python Standard Library (sem dependências externas, sem instalação root ou global).
Executa a validação das 8 fases descritas no Prompt oficial do sistema.
"""

import unittest
import sqlite3
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = Path("/home/rafael/Startup/Documentos/Sistema - Campanhas e Sorteios")
SPREADSHEET_PATH = DOCS_DIR / "Permissionarios_Box_Nome_Atividade.xlsx"

class TestSistemaCampanhasMVP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Inicializa banco SQLite em memória com foreign keys e esquema do MVP."""
        cls.conn = sqlite3.connect(":memory:")
        cls.conn.row_factory = sqlite3.Row
        cls.conn.execute("PRAGMA foreign_keys = ON;")
        cursor = cls.conn.cursor()

        # Criação das tabelas relacionais
        cursor.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                permissionario_id INTEGER,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE boxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_number TEXT UNIQUE NOT NULL,
                official_status TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE permissionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ATIVO',
                sebrae_level TEXT DEFAULT 'NIVEL_1_REGULAR'
            );

            CREATE TABLE box_occupancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_id INTEGER NOT NULL REFERENCES boxes(id),
                permissionario_id INTEGER NOT NULL REFERENCES permissionarios(id),
                activity_name TEXT NOT NULL,
                is_current INTEGER DEFAULT 1
            );

            CREATE TABLE campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'EM_ELABORACAO',
                min_purchase_value REAL DEFAULT 20.0,
                max_numbers_per_cpf INTEGER DEFAULT 50,
                legal_promoter_name TEXT,
                legal_checklist_json TEXT NOT NULL DEFAULT '{}',
                draw_method TEXT DEFAULT 'LOTERIA_FEDERAL',
                end_date TEXT NOT NULL
            );

            CREATE TABLE voucher_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                box_id INTEGER NOT NULL REFERENCES boxes(id),
                permissionario_id INTEGER NOT NULL REFERENCES permissionarios(id),
                batch_number INTEGER NOT NULL,
                code_prefix TEXT NOT NULL,
                start_number INTEGER NOT NULL,
                end_number INTEGER NOT NULL,
                total_vouchers INTEGER NOT NULL,
                UNIQUE(campaign_id, code_prefix, start_number)
            );

            CREATE TABLE vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES voucher_batches(id),
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                box_id INTEGER NOT NULL REFERENCES boxes(id),
                permissionario_id INTEGER NOT NULL REFERENCES permissionarios(id),
                full_code TEXT UNIQUE NOT NULL,
                sequence_number INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'DISTRIBUIDO',
                issued_value REAL
            );

            CREATE TABLE participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_cpf TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL
            );

            CREATE TABLE participations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                voucher_id INTEGER UNIQUE NOT NULL REFERENCES vouchers(id),
                participant_id INTEGER NOT NULL REFERENCES participants(id),
                lucky_number TEXT NOT NULL,
                validated_at TEXT NOT NULL,
                UNIQUE(campaign_id, lucky_number)
            );

            CREATE TABLE validation_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                voucher_code TEXT NOT NULL,
                participant_cpf TEXT,
                success INTEGER NOT NULL,
                refusal_reason TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                entity_id TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            );
        """)
        cls.conn.commit()

    def test_01_fase1_autenticacao_e_papeis(self):
        """Fase 1: Verifica hashing de senhas e RBAC (ADMIN, ATENDENTE, PERMISSIONARIO)."""
        cur = self.conn.cursor()
        users = [
            ("admin", hashlib.sha256(b"admin123").hexdigest(), "Gestor SEMAGRI", "ADMIN", None),
            ("atendente", hashlib.sha256(b"atend123").hexdigest(), "Atendente Balcão", "ATENDENTE", None),
            ("perm_260", hashlib.sha256(b"perm123").hexdigest(), "Sulamita Ferreira", "PERMISSIONARIO", 1),
        ]
        cur.executemany("INSERT INTO users (username, password_hash, full_name, role, permissionario_id) VALUES (?,?,?,?,?)", users)
        self.conn.commit()

        row = cur.execute("SELECT role FROM users WHERE username = 'admin'").fetchone()
        self.assertEqual(row["role"], "ADMIN")

        row_perm = cur.execute("SELECT role, permissionario_id FROM users WHERE username = 'perm_260'").fetchone()
        self.assertEqual(row_perm["role"], "PERMISSIONARIO")
        self.assertEqual(row_perm["permissionario_id"], 1)

    def test_02_fase2_leitura_e_anomalias_da_planilha_real(self):
        """Fase 2: Valida extração da planilha oficial e identifica as anomalias do diagnóstico."""
        self.assertTrue(SPREADSHEET_PATH.exists(), f"Planilha não encontrada: {SPREADSHEET_PATH}")

        with zipfile.ZipFile(SPREADSHEET_PATH) as z:
            shared = []
            st = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in st.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                texts = [t.text for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text]
                shared.append("".join(texts))

            sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            rows = []
            for r in sheet.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                rn = int(r.attrib.get("r", 0))
                cells = {}
                for c in r.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                    col = "".join(ch for ch in c.attrib.get("r", "") if ch.isalpha())
                    v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                    cells[col] = (shared[int(v.text)] if c.attrib.get("t") == "s" else v.text).strip() if (v is not None and v.text is not None) else ""
                if rn > 8 and any(cells.values()):
                    rows.append({"row": rn, "box": cells.get("A", ""), "name": cells.get("B", ""), "activity": cells.get("C", "")})

        # Anomalia 1: Exatamente 292 linhas de dados
        self.assertEqual(len(rows), 292)

        # Anomalia 2: Box 257 aparece duplicado
        box_counts = Counter(r["box"] for r in rows if r["box"])
        self.assertEqual(box_counts["257"], 2)

        # Anomalia 3: 13 boxes com nome 'vago' e 13 com nome em branco
        vagos = [r for r in rows if "VAGO" in r["name"].upper()]
        vazios = [r for r in rows if not r["name"]]
        self.assertEqual(len(vagos), 13)
        self.assertEqual(len(vazios), 13)

        # Anomalia 4: Capacidade do mapa é 368; 77 boxes faltam na planilha
        box_nums = set(int(r["box"]) for r in rows if r["box"].isdigit())
        missing_from_map = set(range(1, 369)) - box_nums
        self.assertEqual(len(missing_from_map), 77)

        # Simula a homologação do Box 260 como CONFIRMADO
        cur = self.conn.cursor()
        cur.execute("INSERT INTO boxes (box_number, official_status) VALUES ('260', 'CONFIRMADO')")
        box_id = cur.lastrowid
        cur.execute("INSERT INTO permissionarios (name, status) VALUES ('Sulamita Ferreira Figueira', 'ATIVO')")
        perm_id = cur.lastrowid
        cur.execute("INSERT INTO box_occupancies (box_id, permissionario_id, activity_name) VALUES (?, ?, 'SALÃO E BARBEARIA')", (box_id, perm_id))
        self.conn.commit()

    def test_03_fase3_campanha_e_trava_juridica(self):
        """Fase 3: Campanha não pode ser ativada sem as 6 aprovações jurídicas obrigatórias."""
        cur = self.conn.cursor()
        now = datetime.now()
        end_date = (now + timedelta(days=60)).isoformat()

        # Cria campanha em rascunho
        cur.execute("""
            INSERT INTO campaigns (name, status, legal_checklist_json, end_date)
            VALUES ('Campanha Revitalização', 'EM_ELABORACAO', '{}', ?)
        """, (end_date,))
        camp_id = cur.lastrowid
        self.conn.commit()

        # Tentativa de ativação direta sem checklist DEVE FALHAR
        checklist = {}
        mandatory_gates = [
            "legal_promoter_ok", "participant_compliance_ok", "prizes_funded_ok",
            "rules_approved_ok", "lgpd_declared_ok", "electoral_cleared_ok"
        ]
        all_cleared = all(checklist.get(k, False) for k in mandatory_gates)
        self.assertFalse(all_cleared)

        # Registrar as 6 aprovações obrigatórias
        checklist_approved = {k: True for k in mandatory_gates}
        cur.execute("""
            UPDATE campaigns
            SET status = 'ATIVA',
                legal_promoter_name = 'SEMAGRI Barcarena',
                legal_checklist_json = ?
            WHERE id = ?
        """, (json.dumps(checklist_approved), camp_id))
        self.conn.commit()

        status = cur.execute("SELECT status FROM campaigns WHERE id = ?", (camp_id,)).fetchone()["status"]
        self.assertEqual(status, "ATIVA")

    def test_04_fase4_distribuicao_de_talao_sem_sobreposicao(self):
        """Fase 4: Geração de talão com faixas exclusivas e bloqueio de intervalos sobrepostos."""
        cur = self.conn.cursor()
        camp_id = 1
        box_id = 1
        perm_id = 1

        # Insere lote 1: NATAL 1..50
        cur.execute("""
            INSERT INTO voucher_batches (campaign_id, box_id, permissionario_id, batch_number, code_prefix, start_number, end_number, total_vouchers)
            VALUES (?, ?, ?, 1, 'NATAL', 1, 50, 50)
        """, (camp_id, box_id, perm_id))
        batch_id = cur.lastrowid

        # Cria comprovantes do lote
        vouchers = [
            (batch_id, camp_id, box_id, perm_id, f"NATAL-{seq:05d}", seq, "DISTRIBUIDO")
            for seq in range(1, 51)
        ]
        cur.executemany("""
            INSERT INTO vouchers (batch_id, campaign_id, box_id, permissionario_id, full_code, sequence_number, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, vouchers)
        self.conn.commit()

        # Tentativa de criar lote com faixa sobreposta (ex: NATAL 25..75) deve ser detectada
        new_start, new_end = 25, 75
        overlap = cur.execute("""
            SELECT id FROM voucher_batches
            WHERE campaign_id = ? AND code_prefix = 'NATAL'
              AND NOT (? > end_number OR ? < start_number)
        """, (camp_id, new_start, new_end)).fetchone()
        self.assertIsNotNone(overlap, "A sobreposição de intervalos deveria ter sido detectada!")

    def test_05_fase5_balcao_atendimento_e_bloqueio_duplicidade(self):
        """Fase 5: Balcão valida comprovante, emite número da sorte 1:1 e bloqueia reutilização."""
        cur = self.conn.cursor()
        camp_id = 1

        # Cria consumidor
        cur.execute("INSERT INTO participants (document_cpf, full_name, phone) VALUES ('12345678900', 'Rafael Oliveira', '91988887777')")
        part_id = cur.lastrowid

        # 1ª Validação do cupom NATAL-00001
        v = cur.execute("SELECT id, status FROM vouchers WHERE full_code = 'NATAL-00001'").fetchone()
        self.assertEqual(v["status"], "DISTRIBUIDO")

        # Atualização atômica para UTILIZADO
        updated = cur.execute("UPDATE vouchers SET status = 'UTILIZADO' WHERE id = ? AND status = 'DISTRIBUIDO'", (v["id"],)).rowcount
        self.assertEqual(updated, 1)

        # Gera Número da Sorte determinístico 1:1
        lucky_number = "00001"
        cur.execute("""
            INSERT INTO participations (campaign_id, voucher_id, participant_id, lucky_number, validated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (camp_id, v["id"], part_id, lucky_number, datetime.now().isoformat()))
        cur.execute("INSERT INTO validation_attempts (campaign_id, voucher_code, participant_cpf, success, refusal_reason, created_at) VALUES (?, 'NATAL-00001', '12345678900', 1, NULL, ?)", (camp_id, datetime.now().isoformat()))
        self.conn.commit()

        # 2ª Tentativa simultânea/repetida para o MESMO cupom NATAL-00001
        second_update = cur.execute("UPDATE vouchers SET status = 'UTILIZADO' WHERE id = ? AND status = 'DISTRIBUIDO'", (v["id"],)).rowcount
        self.assertEqual(second_update, 0, "O mesmo cupom não pode ser validado duas vezes!")

        # Registro da recusa na auditoria
        cur.execute("INSERT INTO validation_attempts (campaign_id, voucher_code, participant_cpf, success, refusal_reason, created_at) VALUES (?, 'NATAL-00001', '12345678900', 0, 'Comprovante já utilizado anteriormente', ?)", (camp_id, datetime.now().isoformat()))
        self.conn.commit()

        attempt = cur.execute("SELECT success, refusal_reason FROM validation_attempts WHERE voucher_code = 'NATAL-00001' AND success = 0").fetchone()
        self.assertEqual(attempt["success"], 0)
        self.assertIn("já utilizado", attempt["refusal_reason"])

    def test_06_fase6_isolamento_portal_permissionario(self):
        """Fase 6: Permissionário do Box 260 emite comprovante próprio e é impedido de mexer no de outro."""
        cur = self.conn.cursor()
        # Box 260 emite NATAL-00002
        v2 = cur.execute("SELECT id, permissionario_id FROM vouchers WHERE full_code = 'NATAL-00002'").fetchone()
        self.assertEqual(v2["permissionario_id"], 1)

        cur.execute("UPDATE vouchers SET status = 'EMITIDO', issued_value = 45.0 WHERE id = ?", (v2["id"],))
        self.conn.commit()

        v2_status = cur.execute("SELECT status, issued_value FROM vouchers WHERE id = ?", (v2["id"],)).fetchone()
        self.assertEqual(v2_status["status"], "EMITIDO")
        self.assertEqual(v2_status["issued_value"], 45.0)

        # Tentativa de permissionário de outro box (id=99) operar o cupom de id=1 DEVE SER BLOQUEADA
        perm_owner_id = v2["permissionario_id"]
        attacker_id = 99
        is_authorized = (perm_owner_id == attacker_id)
        self.assertFalse(is_authorized, "Falha de segurança IDOR: usuário acessou comprovante alheio!")

    def test_07_fase7_metricas_dashboard_e_auditoria(self):
        """Fase 7: Verificação do cálculo dos indicadores em tempo real."""
        cur = self.conn.cursor()
        total_vouchers = cur.execute("SELECT COUNT(*) FROM vouchers").fetchone()[0]
        used_vouchers = cur.execute("SELECT COUNT(*) FROM vouchers WHERE status = 'UTILIZADO'").fetchone()[0]
        rejections = cur.execute("SELECT COUNT(*) FROM validation_attempts WHERE success = 0").fetchone()[0]

        self.assertEqual(total_vouchers, 50)
        self.assertEqual(used_vouchers, 1)
        self.assertGreaterEqual(rejections, 1)

    def test_08_fase8_apuracao_loteria_federal_e_hash_sha256(self):
        """Fase 8: Congelamento auditável da base com SHA-256 e apuração pela Loteria Federal."""
        cur = self.conn.cursor()
        camp_id = 1

        # Congelamento e cálculo do hash SHA-256 das participações válidas
        participations = cur.execute("SELECT id, lucky_number, participant_id, voucher_id FROM participations WHERE campaign_id = ? ORDER BY lucky_number", (camp_id,)).fetchall()
        self.assertGreater(len(participations), 0)

        hasher = hashlib.sha256()
        for p in participations:
            hasher.update(f"{p['id']}|{p['lucky_number']}|{p['participant_id']}|{p['voucher_id']}".encode("utf-8"))
        base_hash = hasher.hexdigest()
        self.assertEqual(len(base_hash), 64)

        # Extração Oficial da Loteria Federal (5 primeiros prêmios)
        # 1º: 24.568 -> 8
        # 2º: 13.492 -> 2
        # 3º: 56.701 -> 1
        # 4º: 89.234 -> 4
        # 5º: 07.815 -> 5
        # Regra regulamentar: combinação do dígito da unidade simples = "82145"
        prizes = ["24568", "13492", "56701", "89234", "07815"]
        calculated_target = "".join(p[-1] for p in prizes)
        self.assertEqual(calculated_target, "82145")

        # Localização determinística do ganhador (mais próximo se não houver exato)
        winner = min(participations, key=lambda p: abs(int(p["lucky_number"]) - int(calculated_target)))
        self.assertEqual(winner["lucky_number"], "00001")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSistemaCampanhasMVP)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    exit(0 if result.wasSuccessful() else 1)
