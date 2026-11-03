# Campanhas e Sorteios — Complexo Comercial de Barcarena/PA

Plataforma de gestão de campanhas promocionais, talões, comprovantes, atendimento no balcão e
apuração pela Loteria Federal, para a Prefeitura Municipal de Barcarena (SEICOMTEC).

* **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2
* **Banco:** SQLite (local/demonstração) ou Postgres (via `DATABASE_URL`)
* **Interface:** HTML, CSS e JavaScript sem framework, servidos pelo próprio FastAPI
* **Hospedagem:** pronta para a Vercel (detecção automática de FastAPI via `pyproject.toml`)

O diagnóstico completo do MVP anterior, as correções feitas e os pontos que dependem de
validação jurídica estão em **[DIAGNOSTICO.md](DIAGNOSTICO.md)**. Leia antes de usar com dados reais.

---

## Publicar na Vercel (demonstração)

1. Envie esta pasta para um repositório no GitHub.
2. Na Vercel: **Add New → Project**, importe o repositório.
   * *Framework Preset:* **FastAPI** (a Vercel detecta sozinha pelo `pyproject.toml`).
   * Não é preciso comando de build nem diretório de saída.
3. Em **Settings → Environment Variables**, cadastre:
   * `DEMO_MODE` = `true`
   * `SECRET_KEY` = uma chave longa e aleatória (`python -c "import secrets;print(secrets.token_urlsafe(48))"`)
4. Clique em **Deploy**. Ao abrir o endereço, a tela de entrada mostra os três perfis de teste.

> **Importante:** sem `DATABASE_URL`, a Vercel guarda o banco em `/tmp`, que é **apagado quando a
> função reinicia** (depois de alguns minutos sem uso ou a cada novo deploy). Para uma demonstração
> rápida, isso basta — o sistema avisa na tela. Para homologação com dados que persistem:
>
> 1. Na Vercel, **Storage → Create Database → Neon (Postgres)** e conecte ao projeto.
> 2. Copie a URL de conexão para a variável `DATABASE_URL` (o sistema aceita `postgres://` ou `postgresql://`).
> 3. Faça um novo deploy. As tabelas são criadas no primeiro acesso.

### Operação real (sem contas de demonstração)

| Variável | Valor |
|---|---|
| `DEMO_MODE` | `false` |
| `SECRET_KEY` | obrigatória |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | administrador inicial (senha com 12+ caracteres) |
| `DATABASE_URL` | obrigatória na prática (Postgres) |

Com `DEMO_MODE=false` nenhuma conta com senha conhecida é criada. O administrador cria as contas
de atendentes e permissionários em **Usuários**.

---

## Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Abra http://localhost:8000. A documentação da API fica em http://localhost:8000/docs.

> Vindo da versão 1? Apague o arquivo `sistema_campanhas.db` antigo: a v2 tem tabelas novas.

### Testes

```bash
pytest -q
```

28 testes cobrem autenticação, perfis, calendário e fluxo jurídico das campanhas, talões,
validação atômica no balcão, isolamento do portal, congelamento da base, regras de apuração,
anulação, ata e exportações.

---

## Contas de demonstração (somente com `DEMO_MODE=true`)

| Perfil | Usuário | Senha | O que faz |
|---|---|---|---|
| Gestor | `admin` | `password123` | Tudo: campanhas, cadastros, apuração, auditoria |
| Atendente | `atendente` | `password123` | Balcão e consulta de comprovantes |
| Permissionário | `permissionario_260` | `password123` | Portal do Box 260 |

Há também `atendente2` (mesma senha), do turno da tarde.

### Dados de demonstração

Com `DEMO_MODE=true`, o primeiro acesso gera uma carga **fictícia** (`app/core/demo_data.py`):

| O quê | Para ver |
|---|---|
| Campanha Piloto (ativa) com 24 boxes, ~230 números da sorte em 14 dias, recusas e ocorrências | Painel, Balcão, Talões |
| Dia das Mães 2026 (encerrada), base congelada, 2 prêmios apurados, entrega registrada | Apuração, ata, auditoria |
| Volta às Aulas 2027 (aguardando aprovação) e Festival do Abacaxi 2027 (em elaboração) | Campanhas e etapas |
| Planilha conferida: 264 boxes confirmados; linhas com divergência pendentes | Mapa dos boxes, Conferência |
| 3 permissionários suspensos | Bloqueios no balcão e em talões |

Os comprovantes `NATAL-00001` a `NATAL-00050` (Box 260) ficam livres para testar o balcão.
Use um CPF válido, como `529.982.247-25`.

---

## Roteiro rápido de demonstração

1. **Gestor → Permissionários e boxes → Conferência da planilha:** aprove algumas linhas; os boxes ficam verdes no mapa.
2. **Gestor → Talões e comprovantes → Novo lote:** distribua um lote para um box recém-confirmado.
3. **Atendente → Balcão:** digite `NATAL-00001`, Enter, informe o CPF e gere o número da sorte. Tente o mesmo código de novo para ver a recusa.
4. **Permissionário → Meu box:** registre a entrega de um comprovante e veja o QR Code.
5. **Gestor → Apuração:** encerre as participações, congele a base, registre os 5 prêmios da extração e emita a ata.
6. **Gestor → Auditoria e relatórios:** filtre o histórico e exporte em Excel.

---

## Estrutura

```
pyproject.toml          indica à Vercel onde está o app (app.main:app)
app/main.py             aplicação FastAPI (inicializa o banco no primeiro acesso)
app/core/               configuração, banco, segurança, dados iniciais
app/models/entities.py  modelo de dados
app/services/           regras de negócio (campanhas, talões, balcão, portal, apuração, relatórios)
app/api/routes.py       API REST /api/v1
public/                 interface servida pela CDN (index.html, static/*.js, static/styles.css, static/img)
data/                   planilha oficial de permissionários
tests/                  testes automatizados
legado/                 versão autônoma anterior (só referência)
```
