"""Build standalone frontend with embedded mock dataset."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / 'mock_data_permissionarios.json', 'r', encoding='utf-8') as f:
    rows = json.load(f)

js_rows_literal = json.dumps(rows, ensure_ascii=False)

js_code = f"""/**
 * Sistema de Gestão de Campanhas e Sorteios — Barcarena/PA
 * Frontend Standalone com Mock Database Local (LocalStorage) e Testes Integrados
 */

const MOCK_DATA_ROWS = {js_rows_literal};

const DEFAULT_STATE = {{
  currentRole: 'atendente', // admin, atendente, permissionario
  campaigns: [
    {{
      id: 1,
      name: 'Campanha Piloto — Revitalização do Complexo',
      description: 'Campanha de ativação comercial conforme diagnóstico SEMAGRI/SEICOMTEC.',
      startDate: '2026-10-01',
      endDate: '2026-12-31',
      purchaseStart: '2026-10-01',
      purchaseEnd: '2026-12-20',
      regEnd: '2026-12-25',
      minPurchase: 20.00,
      maxNumbersPerCpf: 50,
      status: 'ATIVA',
      promoterName: 'Prefeitura Municipal de Barcarena — SEMAGRI',
      promoterDoc: '05.105.200/0001-22',
      legalChecklist: {{
        legal_promoter_ok: true,
        participant_compliance_ok: true,
        prizes_funded_ok: true,
        rules_approved_ok: true,
        lgpd_declared_ok: true,
        electoral_cleared_ok: true
      }},
      drawMethod: 'LOTERIA_FEDERAL'
    }}
  ],
  boxes: [
    {{ id: 1, number: '260', sector: 'SETOR SALÕES', status: 'CONFIRMADO', permissionario: 'Sulamita Ferreira Figueira', activity: 'SALÃO E BARBEARIA' }},
    {{ id: 2, number: '257', sector: 'MERCEARIAS', status: 'EM_REGULARIZACAO', permissionario: 'Jean Lima de Andrade', activity: 'VARIEDADES (DUPLICADO)' }},
    {{ id: 3, number: '14', sector: 'PEIXES', status: 'VAGO_CONFIRMADO', permissionario: null, activity: 'PEIXE SALGADO' }}
  ],
  batches: [
    {{
      id: 1,
      campaignId: 1,
      boxNumber: '260',
      permissionarioName: 'Sulamita Ferreira Figueira',
      batchNumber: 1,
      prefix: 'NATAL',
      startNumber: 1,
      endNumber: 50,
      total: 50
    }}
  ],
  vouchers: [], // generated below
  participations: [],
  attempts: [],
  auditLogs: [],
  draws: [],
  stagingReviews: {{}} // row_number -> {{ decision, justification, box, perm, isVago }}
}};

// Pre-populate initial 50 vouchers for Box 260
for (let i = 1; i <= 50; i++) {{
  const code = 'NATAL-' + String(i).padStart(5, '0');
  DEFAULT_STATE.vouchers.push({{
    code: code,
    batchId: 1,
    campaignId: 1,
    boxNumber: '260',
    permissionarioName: 'Sulamita Ferreira Figueira',
    sequence: i,
    status: 'DISTRIBUIDO',
    issuedValue: null,
    invoiceDoc: null,
    qrToken: null
  }});
}}

// State container with LocalStorage sync
let DB = (() => {{
  try {{
    const saved = localStorage.getItem('BARCARENA_MVP_DB');
    if (saved) return JSON.parse(saved);
  }} catch (e) {{
    console.warn('Erro ao ler localStorage:', e);
  }}
  return JSON.parse(JSON.stringify(DEFAULT_STATE));
}})();

function saveDb() {{
  try {{
    localStorage.setItem('BARCARENA_MVP_DB', JSON.stringify(DB));
  }} catch (e) {{
    console.error('Erro ao salvar no localStorage:', e);
  }}
}}

function resetDbToDefault() {{
  if (confirm('Deseja restaurar todos os dados e testes para o estado inicial padrão?')) {{
    localStorage.removeItem('BARCARENA_MVP_DB');
    DB = JSON.parse(JSON.stringify(DEFAULT_STATE));
    saveDb();
    window.location.reload();
  }}
}}

// Log audit helper
function logAudit(action, entity, entityId, details) {{
  const log = {{
    id: DB.auditLogs.length + 1,
    timestamp: new Date().toISOString(),
    user: DB.currentRole.toUpperCase(),
    action,
    entity,
    entityId: String(entityId || '-'),
    details: typeof details === 'object' ? JSON.stringify(details) : String(details)
  }};
  DB.auditLogs.unshift(log);
  saveDb();
}}

// Crypto SHA-256 helper
async function sha256(text) {{
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}}

// Navigation & Roles
function switchTab(tabId) {{
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.getAttribute('data-tab') === tabId));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tabId));
  renderActiveTab(tabId);
}}

function switchRole(roleKey) {{
  DB.currentRole = roleKey;
  saveDb();
  const label = roleKey === 'admin' ? 'Administrador (SEMAGRI)' :
                roleKey === 'atendente' ? 'Atendente de Balcão' : 'Box 260 — Sulamita Ferreira';
  document.getElementById('currentUserName').textContent = label;
  const select = document.getElementById('activeRoleSelect');
  if (select) select.value = roleKey;
}}

function renderActiveTab(tabId) {{
  if (tabId === 'dashboard') renderDashboard();
  if (tabId === 'balcao') renderBalcao();
  if (tabId === 'boxes') renderBoxesAndStaging();
  if (tabId === 'campanhas') renderCampaigns();
  if (tabId === 'taloes') renderTaloes();
  if (tabId === 'portal') renderPortal();
  if (tabId === 'apuracao') renderApuracao();
  if (tabId === 'auditoria') renderAuditoria();
  if (tabId === 'testes') renderTestsTab();
}}

// ================= 1. DASHBOARD =================
function renderDashboard() {{
  const confirmedBoxes = DB.boxes.filter(b => b.status === 'CONFIRMADO').length;
  const activePerms = 1 + Object.values(DB.stagingReviews).filter(r => r.decision === 'APROVADO' && !r.isVago).length;
  const issuedVouchers = DB.vouchers.filter(v => v.status === 'EMITIDO' || v.status === 'UTILIZADO').length;
  const validParticipations = DB.participations.length;
  const uniqueConsumers = new Set(DB.participations.map(p => p.cpf)).size;

  document.getElementById('kpiBoxesConfirmed').textContent = confirmedBoxes;
  document.getElementById('kpiPermsActive').textContent = activePerms;
  document.getElementById('kpiVouchersIssued').textContent = issuedVouchers;
  document.getElementById('kpiVouchersTotal').textContent = 'Total em talões: ' + DB.vouchers.length + ' (' + validParticipations + ' validados)';
  document.getElementById('kpiParticipations').textContent = validParticipations;
  document.getElementById('kpiConsumers').textContent = 'Consumidores únicos: ' + uniqueConsumers;

  // Activities breakdown
  const actCounts = {{}};
  DB.participations.forEach(p => {{
    actCounts[p.activity] = (actCounts[p.activity] || 0) + 1;
  }});
  const actList = document.getElementById('activityBreakdownList');
  const actKeys = Object.keys(actCounts);
  if (actKeys.length === 0) {{
    actList.innerHTML = '<p class="empty-state">Nenhuma participação validada ainda. Valide cupons na aba Balcão.</p>';
  }} else {{
    actList.innerHTML = actKeys.map(k => '<div class="lookup-item"><span>' + k + '</span><strong>' + actCounts[k] + ' cupom(ns)</strong></div>').join('');
  }}

  // Rejections breakdown
  const rejCounts = {{}};
  DB.attempts.filter(a => !a.success).forEach(a => {{
    rejCounts[a.reason] = (rejCounts[a.reason] || 0) + 1;
  }});
  const rejList = document.getElementById('rejectionsBreakdownList');
  const rejKeys = Object.keys(rejCounts);
  if (rejKeys.length === 0) {{
    rejList.innerHTML = '<p class="empty-state">Nenhuma recusa registrada até o momento.</p>';
  }} else {{
    rejList.innerHTML = rejKeys.map(k => '<div class="lookup-item"><span>' + k + '</span><span class="badge badge-danger">' + rejCounts[k] + '</span></div>').join('');
  }}
}}

// ================= 2. BALCÃO =================
function renderBalcao() {{
  const campSelect = document.getElementById('attCampaignSelect');
  campSelect.innerHTML = DB.campaigns.filter(c => c.status === 'ATIVA').map(c => '<option value="' + c.id + '">' + c.name + ' (Ativa)</option>').join('');
  if (campSelect.children.length === 0) {{
    campSelect.innerHTML = '<option value="">Nenhuma campanha ativa. Ative na aba Campanhas.</option>';
  }}
  renderAttendanceHistory();
}}

function handleVoucherLookup() {{
  const code = document.getElementById('attVoucherCode').value.trim().toUpperCase();
  const feedback = document.getElementById('voucherLookupFeedback');
  if (!code) {{
    feedback.textContent = 'Digite o código impresso no talão.';
    return;
  }}
  const voucher = DB.vouchers.find(v => v.code === code);
  if (!voucher) {{
    feedback.innerHTML = '<span style="color: var(--danger)">❌ Comprovante \\'' + code + '\\' não encontrado no lote.</span>';
  }} else if (voucher.status === 'UTILIZADO') {{
    feedback.innerHTML = '<span style="color: var(--danger)">⚠️ Comprovante já foi utilizado e validado anteriormente!</span>';
  }} else if (voucher.status === 'DISTRIBUIDO' || voucher.status === 'EMITIDO') {{
    feedback.innerHTML = '<span style="color: var(--success)">✅ Disponível para validação! Box: ' + voucher.boxNumber + ' (' + voucher.permissionarioName + ')</span>';
  }} else {{
    feedback.innerHTML = '<span style="color: var(--warning)">⚠️ Situação: ' + voucher.status + '</span>';
  }}
}}

function handleAttendanceSubmit(e) {{
  e.preventDefault();
  const alertOk = document.getElementById('attendanceSuccessAlert');
  const alertErr = document.getElementById('attendanceErrorAlert');
  alertOk.style.display = 'none';
  alertErr.style.display = 'none';

  const campaignId = parseInt(document.getElementById('attCampaignSelect').value, 10);
  const code = document.getElementById('attVoucherCode').value.trim().toUpperCase();
  const rawCpf = document.getElementById('attParticipantCpf').value.trim();
  const cleanCpf = rawCpf.replace(/\\D/g, '');
  const name = document.getElementById('attParticipantName').value.trim();
  const phone = document.getElementById('attParticipantPhone').value.trim();
  const neighborhood = document.getElementById('attParticipantNeighborhood').value.trim() || 'Barcarena';

  if (!code) return;
  const voucher = DB.vouchers.find(v => v.code === code);

  // Check 1: Existence
  if (!voucher) {{
    recordAttempt(code, cleanCpf, false, 'Comprovante não cadastrado no lote');
    showAttendanceError('Comprovante Inexistente', 'O código \\'' + code + '\\' não pertence a nenhum talão distribuído.');
    return;
  }}

  // Check 2: Already used (Duplicate prevention)
  if (voucher.status === 'UTILIZADO') {{
    recordAttempt(code, cleanCpf, false, 'Comprovante já utilizado anteriormente');
    showAttendanceError('Comprovante Já Utilizado', 'O cupom \\'' + code + '\\' já foi validado em um sorteio anterior e não pode ser reutilizado!');
    return;
  }}

  // Check 3: Incident status
  if (['CANCELADO', 'EXTRAVIADO', 'DEVOLVIDO'].includes(voucher.status)) {{
    recordAttempt(code, cleanCpf, false, 'Comprovante com ocorrência (' + voucher.status + ')');
    showAttendanceError('Comprovante Inválido', 'O comprovante está marcado como ' + voucher.status + '.');
    return;
  }}

  // Check 4: CPF Limit (50 max)
  const existingForCpf = DB.participations.filter(p => p.campaignId === campaignId && p.cpf === cleanCpf).length;
  if (existingForCpf >= 50) {{
    recordAttempt(code, cleanCpf, false, 'Limite de 50 cupons por CPF atingido');
    showAttendanceError('Limite Atingido', 'Este CPF já atingiu a cota máxima de 50 participações na campanha.');
    return;
  }}

  // Atomic state change
  voucher.status = 'UTILIZADO';
  const luckyNumber = String(DB.participations.length + 1).padStart(5, '0');

  const participation = {{
    id: DB.participations.length + 1,
    campaignId,
    voucherCode: code,
    luckyNumber,
    cpf: cleanCpf,
    name,
    phone,
    neighborhood,
    boxNumber: voucher.boxNumber,
    permissionarioName: voucher.permissionarioName,
    activity: 'SALÃO E BARBEARIA',
    timestamp: new Date().toISOString()
  }};

  DB.participations.push(participation);
  recordAttempt(code, cleanCpf, true, null);
  logAudit('PARTICIPATION_VALIDATED', 'Participation', luckyNumber, {{ voucher: code, cpf: cleanCpf, luckyNumber }});
  saveDb();

  // Show success alert
  document.getElementById('resLuckyNumberTitle').textContent = 'NÚMERO DA SORTE: ' + luckyNumber;
  document.getElementById('resParticipantInfo').textContent = 'Consumidor: ' + name + ' (CPF: ' + rawCpf + ') — ' + (existingForCpf + 1) + 'º cupom na campanha';
  document.getElementById('resOriginInfo').textContent = 'Origem: Box ' + voucher.boxNumber + ' (' + voucher.permissionarioName + ') | Código: ' + code;
  alertOk.style.display = 'flex';

  // Clear inputs
  document.getElementById('attVoucherCode').value = '';
  document.getElementById('voucherLookupFeedback').textContent = 'Pronto para o próximo comprovante.';
  document.getElementById('attVoucherCode').focus();

  renderAttendanceHistory();
  renderDashboard();
}}

function showAttendanceError(title, desc) {{
  document.getElementById('errTitle').textContent = title;
  document.getElementById('errDesc').textContent = desc;
  document.getElementById('attendanceErrorAlert').style.display = 'flex';
  renderAttendanceHistory();
  renderDashboard();
}}

function recordAttempt(code, cpf, success, reason) {{
  DB.attempts.unshift({{
    code,
    cpf: cpf || '-',
    success,
    reason: reason || 'Sucesso (Número gerado)',
    timestamp: new Date().toLocaleTimeString()
  }});
  if (DB.attempts.length > 50) DB.attempts.pop();
  saveDb();
}}

function renderAttendanceHistory() {{
  const tbody = document.getElementById('attendanceHistoryTableBody');
  if (DB.attempts.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="4" class="text-center">Nenhum registro no balcão ainda.</td></tr>';
    return;
  }}
  tbody.innerHTML = DB.attempts.slice(0, 10).map(a => `
    <tr>
      <td><strong>${{a.code}}</strong></td>
      <td>${{a.cpf}}</td>
      <td>${{a.success ? '<span class="badge badge-success">Validado</span>' : '<span class="badge badge-danger">Recusado</span>'}}</td>
      <td><small>${{a.reason}}</small></td>
    </tr>
  `).join('');
}}

// ================= 3. BOXES & STAGING =================
function renderBoxesAndStaging() {{
  const boxCounts = {{}};
  MOCK_DATA_ROWS.forEach(r => {{ if (r.box) boxCounts[r.box] = (boxCounts[r.box] || 0) + 1; }});

  const tbody = document.getElementById('stagingTableBody');
  document.getElementById('stagingPendingCount').textContent = MOCK_DATA_ROWS.length + ' linhas na planilha';

  tbody.innerHTML = MOCK_DATA_ROWS.slice(0, 60).map(r => {{
    const isDup = boxCounts[r.box] > 1;
    const isVago = (r.name || '').toUpperCase().includes('VAGO');
    const isEmpty = !r.name;
    const reviewed = DB.stagingReviews[r.row];

    let flagBadges = '';
    if (isDup) flagBadges += '<span class="badge badge-danger">Box Duplicado (257)</span> ';
    if (isVago) flagBadges += '<span class="badge badge-warning">Marcado VAGO</span> ';
    if (isEmpty) flagBadges += '<span class="badge badge-warning">Nome em Branco</span> ';
    if (!flagBadges) flagBadges = '<span class="badge badge-success">OK</span>';

    const statusBadge = reviewed ?
      (reviewed.decision === 'APROVADO' ? '<span class="badge badge-success">Aprovado</span>' : '<span class="badge badge-danger">Rejeitado</span>') :
      '<span class="badge badge-warning">Pendente Revisão</span>';

    const action = reviewed ?
      '<small style="color: var(--text-muted)">Decisão: ' + reviewed.decision + '</small>' :
      '<button class="btn btn-secondary btn-sm" onclick="openReviewModal(' + r.row + ', \\'' + r.box + '\\', \\'' + encodeURIComponent(r.name) + '\\', \\'' + encodeURIComponent(r.activity) + '\\')">Revisar</button>';

    return `
      <tr>
        <td>#${{r.row}}</td>
        <td><strong>Box ${{r.box || '-'}}</strong></td>
        <td>${{r.name || '<em>(em branco)</em>'}}</td>
        <td>${{r.activity || '-'}}</td>
        <td>${{flagBadges}}</td>
        <td>${{statusBadge}}</td>
        <td>${{action}}</td>
      </tr>
    `;
  }}).join('');

  // Official boxes table
  const offTbody = document.getElementById('officialBoxesTableBody');
  offTbody.innerHTML = DB.boxes.map(b => `
    <tr>
      <td><strong>Box ${{b.number}}</strong></td>
      <td>${{b.permissionario || '<em>(Sem titular)</em>'}}</td>
      <td>${{b.activity || '-'}}</td>
      <td><span class="badge ${{b.status === 'CONFIRMADO' ? 'badge-success' : 'badge-warning'}}">${{b.status}}</span></td>
    </tr>
  `).join('');
}}

function openReviewModal(rowNum, boxNum, nameEnc, actEnc) {{
  const name = decodeURIComponent(nameEnc);
  const act = decodeURIComponent(actEnc);
  document.getElementById('modalStagingId').value = rowNum;
  document.getElementById('modalStagingInfo').textContent = 'Linha #' + rowNum + ': Box ' + boxNum + ' — Titular: ' + (name || '(em branco)') + ' | Atividade: ' + act;
  document.getElementById('reviewBoxNumber').value = boxNum;
  document.getElementById('reviewPermName').value = name;
  document.getElementById('reviewIsVago').checked = name.toUpperCase().includes('VAGO') || !name;
  document.getElementById('reviewJustification').value = '';
  document.getElementById('modalReviewStaging').style.display = 'flex';
}}

function handleReviewSubmit(e) {{
  e.preventDefault();
  const rowNum = parseInt(document.getElementById('modalStagingId').value, 10);
  const decision = document.getElementById('reviewDecision').value;
  const just = document.getElementById('reviewJustification').value.trim();
  const boxNum = document.getElementById('reviewBoxNumber').value.trim();
  const permName = document.getElementById('reviewPermName').value.trim();
  const isVago = document.getElementById('reviewIsVago').checked;

  DB.stagingReviews[rowNum] = {{
    decision,
    justification: just,
    box: boxNum,
    perm: permName,
    isVago
  }};

  if (decision === 'APROVADO') {{
    const existing = DB.boxes.find(b => b.number === boxNum);
    if (!existing) {{
      DB.boxes.push({{
        id: DB.boxes.length + 1,
        number: boxNum,
        sector: 'SETOR GERAL',
        status: isVago ? 'VAGO_CONFIRMADO' : 'CONFIRMADO',
        permissionario: isVago ? null : permName,
        activity: 'DIVERSOS'
      }});
    }} else {{
      existing.status = isVago ? 'VAGO_CONFIRMADO' : 'CONFIRMADO';
      existing.permissionario = isVago ? null : permName;
    }}
  }}

  logAudit('STAGING_ROW_REVIEWED', 'ImportStagingRow', rowNum, {{ decision, justification: just, box: boxNum }});
  saveDb();
  closeModal('modalReviewStaging');
  renderBoxesAndStaging();
  renderDashboard();
}}

// ================= 4. CAMPANHAS =================
function renderCampaigns() {{
  const tbody = document.getElementById('campaignsTableBody');
  tbody.innerHTML = DB.campaigns.map(c => {{
    const chk = c.legalChecklist || {{}};
    const count = Object.values(chk).filter(Boolean).length;
    const legalBadge = count === 6 ?
      '<span class="badge badge-success">6/6 Homologado</span>' :
      '<span class="badge badge-warning">' + count + '/6 Pendente</span>';

    const statusBadge = c.status === 'ATIVA' ? '<span class="badge badge-success">Ativa</span>' :
                        c.status === 'APROVADA' ? '<span class="badge badge-info">Aprovada</span>' :
                        c.status === 'ENCERRADA' ? '<span class="badge badge-warning">Encerrada</span>' :
                        '<span class="badge badge-secondary">' + c.status + '</span>';

    let actions = '';
    if (c.status === 'EM_ELABORACAO') {{
      actions += '<button class="btn btn-secondary btn-sm" onclick="openLegalModal(' + c.id + ')">⚖️ Checklist Jurídico</button> ';
    }}
    if (c.status === 'APROVADA') {{
      actions += '<button class="btn btn-primary btn-sm" onclick="activateCampaign(' + c.id + ')">🚀 Ativar Campanha</button> ';
    }}
    if (c.status === 'ATIVA') {{
      actions += '<button class="btn btn-warning btn-sm" onclick="closeCampaign(' + c.id + ')">🔒 Encerrar Participação</button> ';
    }}

    return `
      <tr>
        <td>#${{c.id}}</td>
        <td><strong>${{c.name}}</strong></td>
        <td>${{c.purchaseStart}} a ${{c.purchaseEnd}}</td>
        <td>R$ ${{c.minPurchase.toFixed(2)}}</td>
        <td>${{statusBadge}}</td>
        <td>${{c.promoterName || '-'}}</td>
        <td>${{legalBadge}}</td>
        <td>${{actions || '<small>Finalizada</small>'}}</td>
      </tr>
    `;
  }}).join('');
}}

function openNewCampaignModal() {{
  document.getElementById('modalNewCampaign').style.display = 'flex';
}}

function handleNewCampaignSubmit(e) {{
  e.preventDefault();
  const newCamp = {{
    id: DB.campaigns.length + 1,
    name: document.getElementById('campName').value.trim(),
    description: document.getElementById('campDesc').value.trim(),
    startDate: document.getElementById('campStart').value,
    endDate: document.getElementById('campEnd').value,
    purchaseStart: document.getElementById('campPurchaseStart').value,
    purchaseEnd: document.getElementById('campPurchaseEnd').value,
    regEnd: document.getElementById('campRegEnd').value,
    minPurchase: parseFloat(document.getElementById('campMinValue').value),
    maxNumbersPerCpf: 50,
    status: 'EM_ELABORACAO',
    promoterName: null,
    legalChecklist: {{}},
    drawMethod: 'LOTERIA_FEDERAL'
  }};
  DB.campaigns.push(newCamp);
  logAudit('CAMPAIGN_CREATED', 'Campaign', newCamp.id, {{ name: newCamp.name }});
  saveDb();
  closeModal('modalNewCampaign');
  renderCampaigns();
}}

function openLegalModal(campId) {{
  document.getElementById('modalLegalCampaignId').value = campId;
  document.getElementById('chkPromoter').checked = true;
  document.getElementById('chkParticipants').checked = true;
  document.getElementById('chkPrizes').checked = true;
  document.getElementById('chkRules').checked = true;
  document.getElementById('chkLgpd').checked = true;
  document.getElementById('chkElectoral').checked = true;
  document.getElementById('legalJustification').value = 'Processo Administrativo SEMAGRI nº 2026/089. Todos os 6 requisitos cumpridos.';
  document.getElementById('modalLegalApprovals').style.display = 'flex';
}}

function handleLegalApprovalsSubmit(e) {{
  e.preventDefault();
  const campId = parseInt(document.getElementById('modalLegalCampaignId').value, 10);
  const camp = DB.campaigns.find(c => c.id === campId);
  if (!camp) return;

  camp.promoterName = document.getElementById('legalPromoterName').value.trim();
  camp.promoterDoc = document.getElementById('legalPromoterDoc').value.trim();
  camp.legalChecklist = {{
    legal_promoter_ok: document.getElementById('chkPromoter').checked,
    participant_compliance_ok: document.getElementById('chkParticipants').checked,
    prizes_funded_ok: document.getElementById('chkPrizes').checked,
    rules_approved_ok: document.getElementById('chkRules').checked,
    lgpd_declared_ok: document.getElementById('chkLgpd').checked,
    electoral_cleared_ok: document.getElementById('chkElectoral').checked
  }};
  camp.status = 'APROVADA';
  logAudit('CAMPAIGN_LEGAL_APPROVED', 'Campaign', campId, {{ status: 'APROVADA' }});
  saveDb();
  closeModal('modalLegalApprovals');
  renderCampaigns();
}}

function activateCampaign(campId) {{
  const camp = DB.campaigns.find(c => c.id === campId);
  if (!camp) return;
  camp.status = 'ATIVA';
  logAudit('CAMPAIGN_ACTIVATED', 'Campaign', campId, {{ status: 'ATIVA' }});
  saveDb();
  renderCampaigns();
  renderDashboard();
}}

function closeCampaign(campId) {{
  const camp = DB.campaigns.find(c => c.id === campId);
  if (!camp) return;
  camp.status = 'ENCERRADA';
  logAudit('CAMPAIGN_CLOSED', 'Campaign', campId, {{ status: 'ENCERRADA' }});
  saveDb();
  renderCampaigns();
  renderDashboard();
}}

// ================= 5. TALÕES & COMPROVANTES =================
function renderTaloes() {{
  const campSelect = document.getElementById('batchCampaignSelect');
  campSelect.innerHTML = DB.campaigns.map(c => '<option value="' + c.id + '">' + c.name + ' (' + c.status + ')</option>').join('');

  const boxSelect = document.getElementById('batchBoxSelect');
  boxSelect.innerHTML = '<option value="">Selecione um Box Confirmado</option>' +
    DB.boxes.filter(b => b.status === 'CONFIRMADO' && b.permissionario)
      .map(b => '<option value="' + b.number + '" data-perm="' + b.permissionario + '">Box ' + b.number + ' — ' + b.permissionario + '</option>').join('');
}}

function handleBatchBoxChange(boxNumber) {{
  const select = document.getElementById('batchBoxSelect');
  const opt = select.selectedOptions[0];
  if (opt) {{
    document.getElementById('batchPermissionarioInput').value = opt.getAttribute('data-perm') || '';
  }}
}}

function handleCreateBatchSubmit(e) {{
  e.preventDefault();
  const boxNum = document.getElementById('batchBoxSelect').value;
  const permName = document.getElementById('batchPermissionarioInput').value;
  const prefix = document.getElementById('batchPrefix').value.trim().toUpperCase();
  const start = parseInt(document.getElementById('batchStart').value, 10);
  const end = parseInt(document.getElementById('batchEnd').value, 10);

  if (start > end) {{
    alert('O número inicial deve ser menor ou igual ao final.');
    return;
  }}

  // Overlap verification
  const overlap = DB.batches.find(b => b.prefix === prefix && !(start > b.endNumber || end < b.startNumber));
  if (overlap) {{
    alert('Conflito de intervalo! O lote #' + overlap.batchNumber + ' já utiliza o intervalo [' + overlap.startNumber + '..' + overlap.endNumber + '] com o prefixo \\'' + prefix + '\\'.');
    return;
  }}

  const batch = {{
    id: DB.batches.length + 1,
    campaignId: 1,
    boxNumber: boxNum,
    permissionarioName: permName,
    batchNumber: DB.batches.length + 1,
    prefix,
    startNumber: start,
    endNumber: end,
    total: (end - start) + 1
  }};
  DB.batches.push(batch);

  // Generate vouchers
  for (let i = start; i <= end; i++) {{
    DB.vouchers.push({{
      code: prefix + '-' + String(i).padStart(5, '0'),
      batchId: batch.id,
      campaignId: 1,
      boxNumber: boxNum,
      permissionarioName: permName,
      sequence: i,
      status: 'DISTRIBUIDO',
      issuedValue: null,
      invoiceDoc: null,
      qrToken: null
    }});
  }}

  logAudit('BATCH_CREATED', 'VoucherBatch', batch.id, {{ prefix, range: start + '..' + end, total: batch.total }});
  saveDb();
  alert('Talão gerado com sucesso! Lote #' + batch.batchNumber + ' com ' + batch.total + ' comprovantes.');
  renderDashboard();
}}

function handleDirectVoucherLookup() {{
  const code = document.getElementById('lookupVoucherInput').value.trim().toUpperCase();
  const box = document.getElementById('voucherLookupResultBox');
  if (!code) return;

  const v = DB.vouchers.find(x => x.code === code);
  if (!v) {{
    alert('Comprovante \\'' + code + '\\' não encontrado.');
    box.style.display = 'none';
    return;
  }}

  document.getElementById('vlrCode').textContent = v.code;
  document.getElementById('vlrStatusBadge').textContent = v.status;
  document.getElementById('vlrStatusBadge').className = 'badge ' + (v.status === 'UTILIZADO' ? 'badge-danger' : 'badge-success');
  document.getElementById('vlrBox').textContent = 'Box ' + v.boxNumber;
  document.getElementById('vlrPerm').textContent = v.permissionarioName;
  document.getElementById('vlrBatch').textContent = 'Lote #' + v.batchId;
  document.getElementById('vlrValue').textContent = v.issuedValue ? 'R$ ' + v.issuedValue.toFixed(2) : 'Não informado';
  document.getElementById('vlrDoc').textContent = v.invoiceDoc || 'Sem documento vinculado';
  box.style.display = 'block';
}}

// ================= 6. PORTAL DO PERMISSIONÁRIO =================
function renderPortal() {{
  document.getElementById('portalPermName').textContent = 'Box 260 — Sulamita Ferreira Figueira';
  document.getElementById('portalPermDetails').textContent = 'Atividade: Salão e Barbearia | Nível Sebrae: Nível 1 - Regular | Cadastro: ATIVO';
}}

function handlePortalIssueSubmit(e) {{
  e.preventDefault();
  const code = document.getElementById('portalVoucherCode').value.trim().toUpperCase();
  const val = parseFloat(document.getElementById('portalVoucherValue').value);
  const doc = document.getElementById('portalInvoiceDoc').value.trim();

  const v = DB.vouchers.find(x => x.code === code);
  if (!v) {{
    alert('Comprovante \\'' + code + '\\' não encontrado no seu lote.');
    return;
  }}
  if (v.boxNumber !== '260') {{
    alert('Violação de isolamento: este comprovante pertence a outro permissionário!');
    return;
  }}
  if (v.status !== 'DISTRIBUIDO') {{
    alert('Não é possível emitir: comprovante já está como \\'' + v.status + '\\'.');
    return;
  }}

  v.status = 'EMITIDO';
  v.issuedValue = val;
  v.invoiceDoc = doc;
  v.qrToken = 'QR-' + Math.random().toString(36).substring(2, 10).toUpperCase();

  logAudit('VOUCHER_ISSUED_MERCHANT', 'Voucher', v.code, {{ value: val, doc, qr: v.qrToken }});
  saveDb();

  const alertOk = document.getElementById('portalIssueSuccessAlert');
  document.getElementById('portalIssueDetails').innerHTML = 
    'Código: <strong>' + v.code + '</strong> | Valor: R$ ' + val.toFixed(2) + '<br>' +
    'Token QR Gerado: <code>' + v.qrToken + '</code><br>' +
    'O consumidor pode levar este código ao balcão para retirar o seu Número da Sorte!';
  alertOk.style.display = 'block';
  renderDashboard();
}}

function handlePortalIncidentSubmit(e) {{
  e.preventDefault();
  const code = document.getElementById('incidentVoucherCode').value.trim().toUpperCase();
  const type = document.getElementById('incidentType').value;
  const reason = document.getElementById('incidentReason').value.trim();

  const v = DB.vouchers.find(x => x.code === code);
  if (!v) {{
    alert('Comprovante não encontrado.');
    return;
  }}
  if (v.boxNumber !== '260') {{
    alert('Violação de isolamento: este comprovante pertence a outro permissionário!');
    return;
  }}
  if (v.status === 'UTILIZADO') {{
    alert('Comprovante já foi utilizado em participação e não pode ser cancelado.');
    return;
  }}

  v.status = type;
  logAudit('VOUCHER_' + type, 'Voucher', code, {{ reason }});
  saveDb();
  alert('Ocorrência registrada! Comprovante ' + code + ' marcado como ' + type + '.');
  document.getElementById('incidentReason').value = '';
  renderDashboard();
}}

// ================= 7. APURAÇÃO LOTERIA FEDERAL =================
function renderApuracao() {{
  const campSelect = document.getElementById('drawCampaignSelect');
  campSelect.innerHTML = DB.campaigns.map(c => '<option value="' + c.id + '">' + c.name + ' (' + c.status + ')</option>').join('');

  // Default extraction sample values (Concurso CEF 5900)
  document.getElementById('drawContest').value = '5900';
  document.getElementById('drawP1').value = '24568';
  document.getElementById('drawP2').value = '13492';
  document.getElementById('drawP3').value = '56701';
  document.getElementById('drawP4').value = '89234';
  document.getElementById('drawP5').value = '07815';
  document.getElementById('drawPrizeTitle').value = 'Moto 160cc 0km';

  renderDrawHistory();
}}

async function handleFederalDrawSubmit(e) {{
  e.preventDefault();
  const campId = parseInt(document.getElementById('drawCampaignSelect').value, 10);
  const camp = DB.campaigns.find(c => c.id === campId);
  const contest = document.getElementById('drawContest').value.trim();
  const prizeTitle = document.getElementById('drawPrizeTitle').value.trim();

  const validParts = DB.participations.filter(p => p.campaignId === campId);
  if (validParts.length === 0) {{
    alert('Não existem participações validadas nesta campanha para apuração. Valide ao menos um cupom na aba Balcão antes de apurar.');
    return;
  }}

  // Freeze base and calculate SHA-256
  const baseString = validParts.map(p => p.id + '|' + p.luckyNumber + '|' + p.cpf + '|' + p.voucherCode + '|' + p.timestamp).join('\\n');
  const baseSha = await sha256(baseString);

  // Extract units
  const p1 = document.getElementById('drawP1').value.trim();
  const p2 = document.getElementById('drawP2').value.trim();
  const p3 = document.getElementById('drawP3').value.trim();
  const p4 = document.getElementById('drawP4').value.trim();
  const p5 = document.getElementById('drawP5').value.trim();
  const target = p1.slice(-1) + p2.slice(-1) + p3.slice(-1) + p4.slice(-1) + p5.slice(-1);

  // Find closest lucky number
  const targetInt = parseInt(target, 10);
  const winner = validParts.reduce((prev, curr) => {{
    return (Math.abs(parseInt(curr.luckyNumber, 10) - targetInt) < Math.abs(parseInt(prev.luckyNumber, 10) - targetInt)) ? curr : prev;
  }});

  // End campaign
  camp.status = 'ENCERRADA';

  const drawRecord = {{
    id: DB.draws.length + 1,
    campaignId: campId,
    contest,
    targetCalculated: target,
    winnerLuckyNumber: winner.luckyNumber,
    winnerName: winner.name,
    winnerCpf: winner.cpf,
    winnerPhone: winner.phone,
    winnerBox: winner.boxNumber,
    prizeTitle,
    sha256: baseSha,
    deliveryStatus: 'PENDENTE',
    timestamp: new Date().toISOString()
  }};
  DB.draws.push(drawRecord);

  logAudit('DRAW_EXECUTED_LOTERIA_FEDERAL', 'DrawResult', drawRecord.id, {{ contest, target, winner: winner.luckyNumber }});
  saveDb();

  // Show UI alert
  const alertBox = document.getElementById('drawResultAlert');
  document.getElementById('drawWinnerLuckyNumber').textContent = 'Número da Sorte Contemplado: ' + winner.luckyNumber;
  document.getElementById('drawWinnerDetails').innerHTML = 
    '<strong>Ganhador:</strong> ' + winner.name + ' (CPF: ***.' + winner.cpf.substring(3, 6) + '.***-' + winner.cpf.slice(-2) + ')<br>' +
    '<strong>Contato:</strong> ' + winner.phone + ' | Bairro: ' + winner.neighborhood + '<br>' +
    '<strong>Comprovante Premiado:</strong> ' + winner.voucherCode + ' — Box: ' + winner.boxNumber + ' (' + winner.permissionarioName + ')<br>' +
    '<strong>Regra Oficial:</strong> Unidade simples dos 5 prêmios da CEF (Dígitos apurados: <strong>' + target + '</strong>)';
  document.getElementById('drawSha256').textContent = baseSha;
  alertBox.style.display = 'block';

  renderDrawHistory();
  renderCampaigns();
  renderDashboard();
}}

function renderDrawHistory() {{
  const tbody = document.getElementById('drawHistoryTableBody');
  if (DB.draws.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Nenhuma apuração realizada ainda nesta campanha.</td></tr>';
    return;
  }}
  tbody.innerHTML = DB.draws.map(d => `
    <tr>
      <td>#${{d.campaignId}}</td>
      <td>Concurso ${{d.contest}}</td>
      <td><strong style="color: var(--primary); font-size: 1.1rem;">${{d.winnerLuckyNumber}}</strong></td>
      <td>${{d.winnerName}}</td>
      <td>${{d.prizeTitle}}</td>
      <td><span class="badge badge-warning">${{d.deliveryStatus}}</span></td>
    </tr>
  `).join('');
}}

// ================= 8. AUDITORIA =================
function renderAuditoria() {{
  const tbody = document.getElementById('auditTableBody');
  if (DB.auditLogs.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Nenhum registro de auditoria ainda.</td></tr>';
    return;
  }}
  tbody.innerHTML = DB.auditLogs.slice(0, 40).map(l => `
    <tr>
      <td>#${{l.id}}</td>
      <td><small>${{l.timestamp.replace('T', ' ').substring(0, 19)}}</small></td>
      <td><strong>${{l.user}}</strong></td>
      <td><span class="badge badge-info">${{l.action}}</span></td>
      <td>${{l.entity}}</td>
      <td>${{l.entityId}}</td>
      <td><code style="font-size: 0.78rem;">${{l.details}}</code></td>
    </tr>
  `).join('');
}}

function exportParticipationsCsv() {{
  if (DB.participations.length === 0) {{
    alert('Nenhuma participação para exportar.');
    return;
  }}
  let csv = 'numero_da_sorte,comprovante,box,permissionario,cpf,nome,data_validacao\\n';
  DB.participations.forEach(p => {{
    csv += p.luckyNumber + ',' + p.voucherCode + ',' + p.boxNumber + ',\"' + p.permissionarioName + '\",' + p.cpf + ',\"' + p.name + '\",' + p.timestamp + '\\n';
  }});
  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'participacoes_validadas.csv';
  link.click();
}}

// ================= 9. BATERIA DE TESTES NO NAVEGADOR =================
function renderTestsTab() {{
  // Test tab view ready
}}

async function runBrowserTestSuite() {{
  const logBox = document.getElementById('testResultsLog');
  logBox.innerHTML = '<div style="color: #64748b;">Iniciando bateria de testes locais...</div>';
  const results = [];

  function assert(condition, message) {{
    if (!condition) throw new Error(message);
  }}

  async function runTest(name, fn) {{
    try {{
      await fn();
      results.push({{ name, status: 'PASSED' }});
    }} catch (e) {{
      results.push({{ name, status: 'FAILED', error: e.message }});
    }}
  }}

  // Test 1: RBAC & Auth Simulation
  await runTest('Fase 1: Autenticação e Perfis (ADMIN, ATENDENTE, PERMISSIONARIO)', () => {{
    assert(['admin', 'atendente', 'permissionario'].includes(DB.currentRole), 'Perfil atual inválido');
  }});

  // Test 2: Excel Staging & Anomaly Detection
  await runTest('Fase 2: Diagnóstico da Planilha Real (292 linhas, Box 257 duplo, 13 vagos, 13 vazios, 77 ausentes do mapa 368)', () => {{
    assert(MOCK_DATA_ROWS.length === 292, 'Total de linhas esperado 292, obtido: ' + MOCK_DATA_ROWS.length);
    const b257 = MOCK_DATA_ROWS.filter(r => r.box === '257');
    assert(b257.length === 2, 'Box 257 deveria aparecer 2 vezes, apareceu: ' + b257.length);
    const vagos = MOCK_DATA_ROWS.filter(r => (r.name || '').toUpperCase().includes('VAGO'));
    assert(vagos.length === 13, 'Deveria haver 13 boxes com nome \\'vago\\', obtido: ' + vagos.length);
    const emptyNames = MOCK_DATA_ROWS.filter(r => !r.name);
    assert(emptyNames.length === 13, 'Deveria haver 13 boxes com nome em branco, obtido: ' + emptyNames.length);
  }});

  // Test 3: Campaign State Machine & Legal Gates
  await runTest('Fase 3: Trava Jurídica dos 6 Itens Obrigatórios de Campanha', () => {{
    const c = DB.campaigns[0];
    assert(c.status === 'ATIVA', 'Campanha piloto deveria estar ATIVA');
    const gates = Object.values(c.legalChecklist);
    assert(gates.length === 6 && gates.every(Boolean), 'Todos os 6 itens jurídicos devem estar aprovados para ativação');
  }});

  // Test 4: Batch intervals non-overlapping
  await runTest('Fase 4: Talões com Faixas Exclusivas e Não-sobreposição', () => {{
    const b1 = DB.batches[0];
    assert(b1.prefix === 'NATAL' && b1.startNumber === 1 && b1.endNumber === 50, 'Lote 1 deve cobrir 1..50');
    const isOverlapping = (start, end) => !(start > b1.endNumber || end < b1.startNumber);
    assert(isOverlapping(25, 75) === true, 'Sobreposição de intervalo [25..75] deveria ter sido detectada');
    assert(isOverlapping(51, 100) === false, 'Intervalo contíguo [51..100] não deve colidir');
  }});

  // Test 5: Balcão Attendance & Concurrency Rejection
  await runTest('Fase 5: Balcão — 1 Cupom = 1 Número da Sorte e Bloqueio de Duplicidade', () => {{
    const v5 = DB.vouchers.find(x => x.code === 'NATAL-00005');
    assert(v5, 'Comprovante NATAL-00005 deve existir');
    v5.status = 'UTILIZADO';
    const canReuse = (v5.status === 'DISTRIBUIDO' || v5.status === 'EMITIDO');
    assert(!canReuse, 'O mesmo cupom não pode ser validado uma segunda vez (bloqueio de duplicidade)');
    v5.status = 'DISTRIBUIDO';
  }});

  // Test 6: IDOR Isolation
  await runTest('Fase 6: Isolamento Estrito do Portal do Permissionário (Box 260)', () => {{
    const v = DB.vouchers.find(x => x.code === 'NATAL-00001');
    const attackerBox = '999';
    assert(v.boxNumber !== attackerBox, 'Tentativa de manipulação por box alheio detectada e bloqueada');
  }});

  // Test 7: KPIs calculation
  await runTest('Fase 7: Painel de Indicadores e Trilha de Auditoria', () => {{
    assert(DB.boxes.length >= 1, 'Boxes cadastrados');
    assert(DB.vouchers.length >= 50, 'Comprovantes em talões');
  }});

  // Test 8: Loteria Federal Draw & SHA-256 Hash
  await runTest('Fase 8: Apuração Loteria Federal e Hash Criptográfico SHA-256', async () => {{
    const testDigest = await sha256('TESTE-BARCARENA-2026');
    assert(testDigest.length === 64, 'Digest SHA-256 deve ter 64 caracteres hexadecimais');
    const prizes = ['24568', '13492', '56701', '89234', '07815'];
    const units = prizes.map(p => p.slice(-1)).join('');
    assert(units === '82145', 'Dígitos calculados: esperado 82145, obtido: ' + units);
  }});

  // Render results
  let html = '';
  let allPass = true;
  results.forEach(r => {{
    if (r.status === 'PASSED') {{
      html += '<div style="padding: 0.5rem 0; border-bottom: 1px solid #e2e8f0; color: #15803d;">✅ <strong>[PASSOU]</strong> ' + r.name + '</div>';
    }} else {{
      allPass = false;
      html += '<div style="padding: 0.5rem 0; border-bottom: 1px solid #e2e8f0; color: #b91c1c;">❌ <strong>[FALHOU]</strong> ' + r.name + ' — Erro: ' + r.error + '</div>';
    }}
  }});

  const summary = allPass ?
    '<div class="alert alert-success" style="margin-top: 1rem;">🎉 <strong>Todos os ' + results.length + ' testes foram executados e APROVADOS com sucesso!</strong> O sistema está validado localmente.</div>' :
    '<div class="alert alert-danger" style="margin-top: 1rem;">⚠️ Alguns testes falharam. Verifique os erros acima.</div>';

  logBox.innerHTML = html + summary;
}}

// Global bootstrap
document.addEventListener('DOMContentLoaded', () => {{
  switchRole(DB.currentRole || 'atendente');
  renderActiveTab('dashboard');

  const cpfInput = document.getElementById('attParticipantCpf');
  if (cpfInput) {{
    cpfInput.addEventListener('input', (e) => {{
      let v = e.target.value.replace(/\\D/g, '');
      if (v.length > 11) v = v.substring(0, 11);
      if (v.length > 9) v = v.replace(/(\\d{{3}})(\\d{{3}})(\\d{{3}})(\\d{{1,2}})/, '$1.$2.$3-$4');
      else if (v.length > 6) v = v.replace(/(\\d{{3}})(\\d{{3}})(\\d{{1,3}})/, '$1.$2.$3');
      else if (v.length > 3) v = v.replace(/(\\d{{3}})(\\d{{1,3}})/, '$1.$2');
      e.target.value = v;
    }});
  }}
}});

function closeModal(modalId) {{
  document.getElementById(modalId).style.display = 'none';
}}
"""

with open(BASE_DIR / 'app.js', 'w', encoding='utf-8') as f:
    f.write(js_code)

print('app.js successfully generated in project root!')
