/* Núcleo da interface: estado, API, ícones, formatação e componentes reutilizáveis. */
'use strict';

const S = {
  token: null,
  user: null,
  info: null,
  campaigns: [],
  campaignId: null,     // campanha de contexto (topo da tela)
  options: null,
};

/* ------------------------------------------------------------------ ícones (traço próprio, 24x24) */
const ICONS = {
  painel: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  balcao: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
  campanha: '<path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1z"/><path d="M15 9a4 4 0 0 1 0 6M18 6a8 8 0 0 1 0 12"/>',
  box: '<path d="M3 9l1.5-5h15L21 9"/><path d="M3 9h18v2a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0z"/><path d="M5 13v8h14v-8M10 21v-5h4v5"/>',
  talao: '<path d="M3 7h18v3a2 2 0 0 0 0 4v3H3v-3a2 2 0 0 0 0-4z"/><path d="M14 7v10" stroke-dasharray="2 2"/>',
  portal: '<path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/><circle cx="12" cy="7" r="4"/>',
  apuracao: '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
  auditoria: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  usuarios: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20v-1a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v1"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M22 20v-1a5 5 0 0 0-4-4.9"/>',
  guia: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 21a2 2 0 0 1 2-2h13v2H6"/><path d="M9 7h6M9 11h4"/>',
  sair: '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"/>',
  busca: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  mais: '<path d="M12 5v14M5 12h14"/>',
  ok: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>',
  erro: '<circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/>',
  alerta: '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17.5v.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.01"/>',
  baixar: '<path d="M12 4v11M7 10l5 5 5-5M4 20h16"/>',
  imprimir: '<path d="M7 8V3h10v5M7 17H4v-6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6h-3"/><path d="M7 14h10v7H7z"/>',
  qr: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3M21 14v.01M14 21h3M21 17v4h-2"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13.5" r="3.5"/>',
  fechar: '<path d="M6 6l12 12M18 6L6 18"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  recolher: '<path d="M15 6l-6 6 6 6"/>',
  cadeado: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  relogio: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  editar: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  historico: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 8v4l3 2"/>',
  escudo: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  seta: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  mapa: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
};
function icon(name, cls = '') {
  return `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`;
}

/* ------------------------------------------------------------------ utilidades */
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const nf = new Intl.NumberFormat('pt-BR');
const fmtN = (n) => (n === null || n === undefined ? '—' : nf.format(n));
const fmtMoney = (n) => (n === null || n === undefined ? '—' : n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }));
const TZ = 'America/Belem';
function asDate(iso) { if (!iso) return null; return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z'); }
function fmtDate(iso) { const d = asDate(iso); return d ? d.toLocaleDateString('pt-BR', { timeZone: TZ }) : '—'; }
function fmtDateTime(iso) { const d = asDate(iso); return d ? d.toLocaleString('pt-BR', { timeZone: TZ, dateStyle: 'short', timeStyle: 'short' }) : '—'; }
function toLocalInput(iso) { const d = asDate(iso); if (!d) return ''; const off = d.getTimezoneOffset(); return new Date(d.getTime() - off * 60000).toISOString().slice(0, 16); }
function fromLocalInput(v) { return v ? new Date(v).toISOString().replace('Z', '') : null; }
function debounce(fn, ms = 300) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function initials(name) { return (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase(); }
function maskCpfInput(el) {
  el.addEventListener('input', () => {
    let v = el.value.replace(/\D/g, '').slice(0, 11);
    if (v.length > 9) v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
    else if (v.length > 6) v = v.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
    else if (v.length > 3) v = v.replace(/(\d{3})(\d{1,3})/, '$1.$2');
    el.value = v;
  });
}
function maskPhoneInput(el) {
  el.addEventListener('input', () => {
    let v = el.value.replace(/\D/g, '').slice(0, 11);
    if (v.length > 6) v = v.replace(/(\d{2})(\d{4,5})(\d{0,4})/, '($1) $2-$3');
    else if (v.length > 2) v = v.replace(/(\d{2})(\d+)/, '($1) $2');
    el.value = v;
  });
}
function cpfValid(raw) {
  const c = (raw || '').replace(/\D/g, '');
  if (c.length !== 11 || /^(\d)\1{10}$/.test(c)) return false;
  for (const n of [9, 10]) {
    let s = 0; for (let i = 0; i < n; i++) s += +c[i] * (n + 1 - i);
    if (((s * 10) % 11) % 10 !== +c[n]) return false;
  }
  return true;
}

/* ------------------------------------------------------------------ API */
class ApiError extends Error { constructor(status, detail) { super(detail); this.status = status; } }
async function api(path, { method = 'GET', body, raw = false } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (S.token) headers.Authorization = `Bearer ${S.token}`;
  let res;
  try {
    res = await fetch(`/api/v1${path}`, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch (e) {
    throw new ApiError(0, 'Sem comunicação com o servidor. Verifique a internet e tente de novo.');
  }
  if (res.status === 401 && S.token && !path.startsWith('/auth/login')) {
    App.sessionExpired();
    throw new ApiError(401, 'Sessão encerrada.');
  }
  if (!res.ok) {
    let detail = res.status >= 500
      ? `O servidor não conseguiu processar a solicitação (erro ${res.status}). Tente de novo em instantes; se persistir, verifique os logs do servidor.`
      : `Erro ${res.status}`;
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') detail = j.detail;
      else if (Array.isArray(j.detail)) detail = j.detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join('; ');
    } catch (_) { /* resposta não-JSON */ }
    throw new ApiError(res.status, detail);
  }
  if (raw) return res;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}
async function downloadFile(path, fallbackName) {
  const res = await api(path, { raw: true });
  const blob = await res.blob();
  const cd = res.headers.get('content-disposition') || '';
  const name = (cd.match(/filename=([^;]+)/) || [])[1] || fallbackName;
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
async function openHtml(path) {
  const win = window.open('', '_blank');
  const html = await api(path);
  if (win) { win.document.open(); win.document.write(html); win.document.close(); }
}
async function withLoading(btn, fn) {
  if (btn) { btn.classList.add('loading'); btn.disabled = true; }
  try { return await fn(); }
  finally { if (btn) { btn.classList.remove('loading'); btn.disabled = false; } }
}

/* ------------------------------------------------------------------ componentes */
function toast(message, kind = 'ok') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.innerHTML = `${icon(kind === 'ok' ? 'ok' : kind === 'bad' ? 'erro' : 'alerta')}<div>${esc(message)}</div>`;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), kind === 'bad' ? 7000 : 4000);
}
function fail(err) { toast(err.message || String(err), 'bad'); }

const STATUS_CHIP = {
  EM_ELABORACAO: ['', 'Em elaboração'], AGUARDANDO_APROVACAO: ['warn', 'Aguardando aprovação'], APROVADA: ['info', 'Aprovada'],
  ATIVA: ['ok', 'Ativa'], ENCERRADA: ['', 'Encerrada'], CANCELADA: ['bad', 'Cancelada'],
  CONFIRMADO: ['ok', 'Confirmado'], VAGO_CONFIRMADO: ['', 'Vago'], EM_REGULARIZACAO: ['warn', 'Em regularização'], SEM_USO: ['', 'Sem uso'],
  PENDENTE_CONFERENCIA: ['warn', 'Aguardando conferência'], SEM_REGISTRO: ['', 'Sem registro'],
  ATIVO: ['ok', 'Ativo'], SUSPENSO: ['warn', 'Suspenso'], INATIVO: ['', 'Inativo'], BLOQUEADO: ['bad', 'Bloqueado'],
  DISTRIBUIDO: ['info', 'Distribuído'], EMITIDO: ['agua', 'Emitido'], UTILIZADO: ['ok', 'Utilizado'],
  CANCELADO: ['bad', 'Cancelado'], DEVOLVIDO: ['warn', 'Devolvido'], EXTRAVIADO: ['bad', 'Extraviado'],
  PENDENTE_REVISAO: ['warn', 'Pendente'], APROVADO: ['ok', 'Aprovado'], REJEITADO: ['bad', 'Rejeitado'], CONCILIADO: ['info', 'Conciliado'],
  VALIDO: ['ok', 'Válido'], ANULADO: ['bad', 'Anulado'],
  PENDENTE: ['warn', 'Pendente'], CONTATADO: ['info', 'Contatado'], ENTREGUE: ['ok', 'Entregue'],
  NAO_LOCALIZADO: ['bad', 'Não localizado'], RECUSADO: ['bad', 'Recusado'], SEM_CONTEMPLADO: ['', 'Sem contemplado'],
  ADMIN: ['info', 'Gestor'], ATENDENTE: ['agua', 'Atendente'], PERMISSIONARIO: ['', 'Permissionário'],
};
function chip(status, label) {
  const [cls, txt] = STATUS_CHIP[status] || ['', status];
  return `<span class="chip ${cls}">${esc(label || txt)}</span>`;
}
function statusLabel(s) { return (STATUS_CHIP[s] || [null, s])[1]; }
const ROLE_LABEL = { ADMIN: 'Gestor', ATENDENTE: 'Atendente do balcão', PERMISSIONARIO: 'Permissionário' };

function emptyState(title, text = '', action = '') {
  return `<div class="empty">${icon('info')}<b>${esc(title)}</b>${text ? `<div>${esc(text)}</div>` : ''}${action ? `<div style="margin-top:12px">${action}</div>` : ''}</div>`;
}
function loadingBlock(lines = 3) { return Array.from({ length: lines }, (_, i) => `<div class="skeleton" style="width:${90 - i * 15}%"></div>`).join(''); }
function errorBlock(err, retry) {
  return `<div class="notice bad">${icon('erro')}<div><b class="nt">Não foi possível carregar.</b>${esc(err.message)}${retry ? ` <button class="btn btn-sm btn-secondary" data-retry>Tentar de novo</button>` : ''}</div></div>`;
}
function howto(title, steps, open = false) {
  return `<details class="howto"${open ? ' open' : ''}><summary>${icon('guia')}${esc(title)}</summary><ol>${steps.map((s) => `<li>${s}</li>`).join('')}</ol></details>`;
}
function notice(kind, title, text) {
  const ic = { ok: 'ok', warn: 'alerta', bad: 'erro', info: 'info' }[kind];
  return `<div class="notice ${kind}">${icon(ic)}<div>${title ? `<b class="nt">${esc(title)}</b>` : ''}${text || ''}</div></div>`;
}
function pageHead(title, desc, actions = '') {
  return `<div class="page-head"><div><h1>${esc(title)}</h1>${desc ? `<p>${desc}</p>` : ''}</div>${actions ? `<div class="page-actions">${actions}</div>` : ''}</div>`;
}
function tabsHtml(tabs, active) {
  return `<div class="tabs" role="tablist">${tabs.map(([k, l]) => `<button role="tab" data-tab="${k}" class="${k === active ? 'active' : ''}" aria-selected="${k === active}">${esc(l)}</button>`).join('')}</div>`;
}
function bindTabs(root, onChange) {
  $$('.tabs button', root).forEach((b) => b.addEventListener('click', () => {
    $$('.tabs button', root).forEach((x) => { x.classList.toggle('active', x === b); x.setAttribute('aria-selected', x === b); });
    onChange(b.dataset.tab);
  }));
}

/* gaveta lateral e modal */
function closeOverlay() { $('#overlay').innerHTML = ''; document.body.style.overflow = ''; }
function openDrawer(title, bodyHtml, { subtitle = '', modal = false } = {}) {
  const ov = $('#overlay');
  ov.innerHTML = `<div class="scrim ${modal ? 'center' : ''}"><div class="${modal ? 'modal' : 'drawer'}" role="dialog" aria-modal="true" aria-label="${esc(title)}">
    <div class="drawer-head"><div><h2>${esc(title)}</h2>${subtitle ? `<small>${subtitle}</small>` : ''}</div><button class="icon-btn" data-close aria-label="Fechar">${icon('fechar')}</button></div>
    <div class="drawer-body">${bodyHtml}</div></div></div>`;
  document.body.style.overflow = 'hidden';
  const scrim = $('.scrim', ov);
  scrim.addEventListener('click', (e) => { if (e.target === scrim) closeOverlay(); });
  $('[data-close]', ov).addEventListener('click', closeOverlay);
  const first = $('input, select, textarea, button:not([data-close])', $('.drawer-body', ov));
  if (first) setTimeout(() => first.focus(), 30);
  return $('.drawer-body', ov);
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && $('#overlay').innerHTML) closeOverlay(); });

/* confirmação com justificativa obrigatória */
function askReason({ title, text, label = 'Justificativa', min = 10, confirm = 'Confirmar', danger = false }) {
  return new Promise((resolve) => {
    const body = openDrawer(title, `<p>${text}</p><div class="field"><label for="rsn">${esc(label)}</label><textarea id="rsn" minlength="${min}"></textarea><div class="hint">Mínimo de ${min} caracteres. Fica registrada na auditoria.</div></div>
      <div class="modal-foot" style="padding:0"><button class="btn btn-secondary" data-no>Voltar</button><button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" data-yes>${esc(confirm)}</button></div>`, { modal: true });
    $('[data-no]', body).onclick = () => { closeOverlay(); resolve(null); };
    $('[data-yes]', body).onclick = () => {
      const v = $('#rsn', body).value.trim();
      if (v.length < min) { $('#rsn', body).classList.add('invalid'); $('#rsn', body).focus(); return; }
      closeOverlay(); resolve(v);
    };
  });
}

function hbars(items, labelKey, valueKey, { empty = 'Sem dados no período.' } = {}) {
  if (!items || !items.length) return emptyState(empty);
  const max = Math.max(...items.map((i) => i[valueKey])) || 1;
  return `<div class="hbars">${items.map((i) => `<div class="hbar"><span title="${esc(i[labelKey])}">${esc(i[labelKey])}</span><div class="track"><b style="width:${(100 * i[valueKey]) / max}%"></b></div><span class="n">${fmtN(i[valueKey])}</span></div>`).join('')}</div>`;
}
function stackBar(parts) {
  const total = parts.reduce((a, p) => a + p.value, 0);
  const bar = total ? parts.filter((p) => p.value).map((p) => `<span style="width:${(100 * p.value) / total}%;background:${p.color}" title="${esc(p.label)}: ${fmtN(p.value)}"></span>`).join('') : '';
  return `<div class="stack" role="img" aria-label="${esc(parts.map((p) => `${p.label} ${p.value}`).join(', '))}">${bar}</div>
    <div class="legend">${parts.map((p) => `<span><i style="background:${p.color}"></i>${esc(p.label)} <b class="num">${fmtN(p.value)}</b></span>`).join('')}</div>`;
}
function campaignOptions(selected, { filter, allLabel } = {}) {
  const list = filter ? S.campaigns.filter(filter) : S.campaigns;
  return (allLabel !== undefined ? `<option value="">${esc(allLabel)}</option>` : '') +
    list.map((c) => `<option value="${c.id}" ${String(c.id) === String(selected) ? 'selected' : ''}>${esc(c.name)} — ${esc(statusLabel(c.status))}</option>`).join('');
}
function currentCampaign() { return S.campaigns.find((c) => String(c.id) === String(S.campaignId)) || null; }
