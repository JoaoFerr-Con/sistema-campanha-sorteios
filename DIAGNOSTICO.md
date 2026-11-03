# Diagnóstico técnico e funcional — versão 2.0

Auditoria do MVP recebido (FastAPI + SQLAlchemy + SQLite + HTML/JS) e registro do que foi alterado.
Cada achado indica a gravidade e o que foi feito. Itens marcados **[VALIDAR]** dependem de decisão
jurídica ou do regulamento e **não** foram decididos pelo sistema.

---

## 1. O que já funcionava e foi preservado

| Funcionalidade | Situação no MVP | Na v2 |
|---|---|---|
| Hash de senha PBKDF2-SHA256 com sal | Correto | Mantido (iterações 120k → 240k) |
| Token assinado HMAC-SHA256 com expiração | Correto | Mantido, agora conferido no banco |
| Máquina de estados da campanha | Correta | Mantida, com novas exigências por etapa |
| Trava jurídica de 6 itens antes da ativação | Correta | Mantida |
| Sobreposição de intervalos de talões | Correta dentro da campanha | Estendida a todas as campanhas |
| Validação atômica do comprovante (UPDATE condicional) | Correta | Mantida |
| Unicidade comprovante → participação | Correta (UNIQUE) | Mantida |
| Importação da planilha para conferência (staging) | Correta | Mantida, com proteção contra reimportação |
| Isolamento do portal (IDOR) | Correto nas operações | Mantido e reforçado |
| Auditoria de operações críticas | Parcial | Ampliada e pesquisável |
| Testes automatizados (8) | Passavam | Mantidos e ajustados; 28 no total |

## 2. Segurança

| # | Achado | Gravidade | Correção |
|---|---|---|---|
| S1 | A interface entrava automaticamente com senhas fixas (`password123`) por um seletor de perfil — qualquer visitante virava administrador | Crítica | Tela de entrada real. Contas de demonstração só existem com `DEMO_MODE=true` e ficam identificadas como tal |
| S2 | Endpoints sem autenticação: indicadores, lista de boxes, lista de permissionários, campanhas, consulta de comprovante e resultado do sorteio (com nome do ganhador) | Alta | Todas as rotas de dados exigem sessão; perfis restritos onde cabe |
| S3 | O perfil era lido do token, sem consultar o banco: usuário desativado continuava operando até o token expirar (24 h) | Alta | Cada requisição confere usuário ativo, perfil e versão de sessão no banco |
| S4 | Sem logout nem invalidação de sessão | Média | `POST /auth/logout` invalida todas as sessões do usuário; troca de senha também |
| S5 | `SECRET_KEY` fixa no código-fonte | Alta | Lida de variável de ambiente; obrigatória fora do modo demonstração |
| S6 | Sem limite de tentativas de login | Média | 5 tentativas por usuário+IP em 5 min (por instância — ver nota de produção) |
| S7 | CPF completo exibido na lista de tentativas do balcão e no log de auditoria | Média (LGPD) | CPF mascarado (`***.456.789-**`) em telas, logs e relatórios; CPF completo só na exportação oficial, que gera registro de auditoria |
| S8 | Caminho local `/home/rafael/...` no código | Baixa | Removido |
| S9 | Erros internos expunham detalhes da exceção no token inválido | Baixa | Mensagens neutras; tratador global de erros 500 |
| S10 | Cabeçalhos de segurança ausentes | Baixa | `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `no-store` na API |
| S11 | XSS: a interface antiga montava HTML com dados do banco sem escapar (nomes da planilha, motivos de recusa) | Média | Nova interface escapa todo conteúdo dinâmico |

**SQL Injection:** não encontrado — todo acesso usa o ORM com parâmetros.
**CSRF:** não se aplica — a autenticação é por cabeçalho `Authorization`, não por cookie.

## 3. Regras de negócio

| # | Achado | Correção |
|---|---|---|
| R1 | Número da sorte calculado como `count(*) + 1`: duas validações simultâneas geravam o mesmo número, a segunda falhava com erro 500 | Contador atômico por campanha (`UPDATE ... SET seq = seq + 1`) |
| R2 | `min_purchase_value` existia mas nunca era verificado | Conferido na emissão pelo portal e no balcão quando o valor é conhecido |
| R3 | Portal emitia comprovante de campanha encerrada e fora do período de compras | Exige campanha ativa e data dentro do período de compras |
| R4 | Balcão aceitava comprovante de permissionário suspenso/bloqueado | Recusa com mensagem "permissionário irregular" (o próprio briefing lista essa mensagem) |
| R5 | CPF aceito só pelo tamanho (11 dígitos) | Dígitos verificadores conferidos; sequências repetidas recusadas |
| R6 | Período de compras podia ficar fora do período da campanha | Validação de calendário completa |
| R7 | Aprovação jurídica podia ser registrada direto da elaboração, pulando "aguardando aprovação" | Aprovação só com a campanha enviada; envio exige etapas 1–5 completas |
| R8 | Campanha ativável sem prêmio e sem regulamento cadastrados | Ativação exige prêmios, referência do regulamento e regra de apuração |
| R9 | Campanha aprovada/ativa podia ter dados alterados pela API | Edição só em elaboração; voltar para elaboração exige justificativa e zera a aprovação |
| R10 | Mesmo prefixo de talão em duas campanhas causava erro 500 (código é único no sistema) | Checagem de sobreposição em todas as campanhas com mensagem clara |
| R11 | Lote sem limite de tamanho (risco de travar o servidor) e prefixo sem validação | Máx. 5.000 comprovantes por lote, numeração até 99999, prefixo alfanumérico |
| R12 | Não havia cancelamento de lote | Cancelamento com justificativa; comprovantes já utilizados são preservados |
| R13 | Reimportar a planilha duplicava toda a área de conferência | Reimportação bloqueada |
| R14 | Revisão em lote aplicava a mesma correção de box/nome a várias linhas | Correções só linha a linha |
| R15 | Nomes da planilha terminam com ponto ("Fulano.") e geravam cadastro duplicado | Ponto final removido na aprovação |
| R16 | Atualização de entrega de prêmio sem auditoria nem histórico | Histórico de eventos de entrega + auditoria; entrega concluída não é alterável |

## 4. Apuração — achados que exigem validação

A regra vigente no MVP: o número de referência é formado pela **unidade simples do 1º ao 5º prêmio**
da Loteria Federal (00000–99999). Se não há número idêntico, vence o **numericamente mais próximo**.

### A1 [VALIDAR] — Concentração de chance (crítico)

Os números da sorte são distribuídos **em sequência a partir de 00001**. Combinado com qualquer regra
de aproximação, isso concentra a chance no último número emitido. Exemplo com 500 participações
(00001 a 00500), regra "mais próximo":

* o número **00500 vence em 99,5% dos resultados possíveis** da Loteria Federal;
* cada um dos demais 499 números tem chance de 0,001%.

A regra "superior, depois inferior" tem o mesmo problema. A regra "somente exato" é equânime, mas em
99,5% das extrações não haveria contemplado.

O sistema **não mudou a distribuição** dos números, porque isso é matéria do regulamento. A tela de
Apuração agora mede e exibe essa concentração para a campanha selecionada. Alternativas usuais, a
decidir com o jurídico:

1. Distribuir os números em séries/faixas que cubram todo o universo (ex.: universo dimensionado
   pela quantidade de participações prevista).
2. Atribuir o número da sorte de forma aleatória e auditável dentro do universo 00000–99999.
3. Usar uma regra de aproximação com "reinício" (após o maior número, volta ao menor) somada a (1).

### A2 [VALIDAR] — Critério de aproximação e desempate

O MVP usava `min(abs(n - alvo))` sem critério de desempate (o vencedor dependia da ordem de leitura
do banco — não reproduzível). Agora:

* a regra é um campo obrigatório da campanha, escolhido entre: **somente exato**, **superior depois
  inferior** ou **mais próximo (empate → superior)**;
* a campanha piloto de demonstração usa "mais próximo", preservando o comportamento anterior;
* **nenhuma regra é assumida** para campanhas novas — o gestor precisa escolher a que está no
  regulamento.

### A3 [VALIDAR] — Contemplado em mais de um prêmio

O sistema não impede que o mesmo CPF vença dois prêmios; apenas avisa no resultado. Confirmar no
regulamento.

### A4 — Corrigido sem alterar a regra

| Achado | Correção |
|---|---|
| Apuração encerrava a campanha automaticamente, sem registro da transição | Exige campanha já encerrada |
| O hash era calculado no momento da apuração (nada estava "congelado") | Etapa formal de congelamento grava hash, contagem e responsável; a apuração confere se a base atual ainda bate |
| O hash não era reproduzível por terceiros | Hash calculado sobre um arquivo CSV canônico que pode ser baixado; qualquer auditor confere com `sha256sum` |
| Zeros à esquerda: aceitava qualquer texto e pegava o último caractere | Cada prêmio precisa ter exatamente 5 algarismos (aceita "07.815") |
| Era possível apurar o mesmo prêmio várias vezes, gerando vencedores diferentes | Um resultado válido por prêmio; refazer exige **anulação formal** com justificativa ≥ 20 caracteres, registrada na auditoria e na ata |
| Sem documentação | Ata de apuração imprimível (salvar em PDF pelo navegador) |

## 5. Integridade e desempenho

* Novos índices: participação por campanha+CPF, comprovante por lote+situação.
* Contagens dos lotes em uma consulta agrupada (antes: 4 consultas por lote).
* SQLite: o modo WAL e `busy_timeout` continuam; o contador atômico resolve a corrida do número da sorte.
* **Migração:** a v2 adiciona colunas e tabelas. Bancos SQLite antigos devem ser recriados (apague
  `sistema_campanhas.db`). Para produção, recomenda-se adotar Alembic antes da primeira carga real.

## 6. LGPD

* Consentimento do participante registrado no balcão (campo obrigatório na tela).
* CPF mascarado em toda exibição; exportação com CPF completo é registrada na auditoria.
* **[VALIDAR]** Prazo de retenção dos dados dos consumidores após a entrega dos prêmios e texto do
  aviso de privacidade — o sistema ainda não executa expurgo automático.

## 7. Implantação na Vercel — limitações conhecidas

* Sem `DATABASE_URL`, o banco fica em `/tmp`, que é **apagado quando a função reinicia** e não é
  compartilhado entre instâncias. Serve só para demonstração; a tela de entrada avisa isso.
* Para homologação com dados que persistem, conecte um Postgres (Neon ou Supabase pelo Marketplace
  da Vercel) e defina `DATABASE_URL`.
* O limite de tentativas de login é por instância; em produção, ative também o Firewall da Vercel.

## 8. Pendências para próximas fases

1. Decisões A1–A3 e retenção LGPD (jurídico).
2. Migrações com Alembic.
3. Expurgo/anonimização programada dos dados de consumidores.
4. Relatórios em PDF gerados no servidor (hoje: ata em HTML imprimível; demais relatórios em Excel/CSV).
5. Notificação ao contemplado (SMS/WhatsApp) com registro no histórico de entrega.
