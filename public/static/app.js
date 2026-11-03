/* Estrutura da aplicação: entrada, navegação por perfil, rotas e contexto de campanha. */
'use strict';

const NAV = [
  { group: 'Visão geral', items: [{ key: 'painel', label: 'Painel', icon: 'painel', roles: ['ADMIN', 'ATENDENTE'] }] },
  { group: 'Operação', items: [
    { key: 'balcao', label: 'Balcão de atendimento', icon: 'balcao', roles: ['ADMIN', 'ATENDENTE'] },
    { key: 'portal', label: 'Meu box', icon: 'portal', roles: ['PERMISSIONARIO'] },
    { key: 'comprovantes', label: 'Talões e comprovantes', icon: 'talao', roles: ['ADMIN'] },
    { key: 'consulta', label: 'Consultar comprovante', icon: 'busca', roles: ['ATENDENTE'] },
  ] },
  { group: 'Gestão', items: [
    { key: 'campanhas', label: 'Campanhas', icon: 'campanha', roles: ['ADMIN'] },
    { key: 'permissionarios', label: 'Permissionários e boxes', icon: 'box', roles: ['ADMIN'] },
    { key: 'portal', label: 'Portal do permissionário', icon: 'portal', roles: ['ADMIN'] },
  ] },
  { group: 'Transparência', items: [
    { key: 'apuracao', label: 'Apuração', icon: 'apuracao', roles: ['ADMIN'] },
    { key: 'auditoria', label: 'Auditoria e relatórios', icon: 'auditoria', roles: ['ADMIN'] },
  ] },
  { group: 'Administração', items: [{ key: 'usuarios', label: 'Usuários', icon: 'usuarios', roles: ['ADMIN'] }] },
  { group: 'Ajuda', items: [{ key: 'guia', label: 'Guia de uso', icon: 'guia', roles: ['ADMIN', 'ATENDENTE', 'PERMISSIONARIO'] }] },
];
const HOME = { ADMIN: 'painel', ATENDENTE: 'balcao', PERMISSIONARIO: 'portal' };
const USES_CAMPAIGN = new Set(['painel', 'balcao', 'comprovantes', 'apuracao']);

const App = {
  async start() {
    try { S.info = await api('/system/info'); } catch (e) { S.info = { demo_mode: false }; }
    const saved = sessionStorage.getItem('cs_token');
    if (saved) {
      S.token = saved;
      try { S.user = await api('/auth/me'); } catch (_) { S.token = null; sessionStorage.removeItem('cs_token'); }
    }
    if (S.user) await this.enter(); else this.renderLogin();
    window.addEventListener('hashchange', () => S.user && this.route());
  },

  /* -------------------------------------------------------------- entrada */
  renderLogin(message) {
    const info = S.info || {};
    const cells = Array.from({ length: 368 }, (_, i) => `<i class="${i === 259 ? 'lucky' : (i * 7919) % 5 < 3 ? 'on' : ''}"></i>`).join('');
    $('#root').innerHTML = `<div class="login">
      <section class="login-brand">
        <div class="login-org"><img src="/static/img/prefeitura-barcarena.png" alt="Prefeitura de Barcarena" height="118"><span>Complexo Comercial de Barcarena<small>Secretaria Municipal de Indústria, Comércio, Tecnologia e Ciência — SEICOMTEC</small></span></div>
        <div>
          <h1>Campanhas e sorteios com transparência</h1>
          <p>Do talão entregue no box ao número da sorte emitido no balcão e à apuração pela Loteria Federal — cada etapa fica registrada e pode ser conferida.</p>
          <div class="login-boxes" aria-hidden="true">${cells}</div>
        </div>
        <div class="login-foot">368 boxes · apuração pela Loteria Federal · base congelada com SHA-256</div>
      </section>
      <section class="login-form-wrap"><form class="login-form" id="loginForm" autocomplete="on">
        <h2>Entrar</h2><p class="muted">Use o usuário e a senha fornecidos pela SEICOMTEC.</p>
        ${message ? notice('warn', '', esc(message)) : ''}
        <div id="loginErr"></div>
        <div class="field"><label for="lu">Usuário</label><input id="lu" name="username" autocomplete="username" required></div>
        <div class="field"><label for="lp">Senha</label><input id="lp" name="password" type="password" autocomplete="current-password" required></div>
        <button class="btn btn-primary btn-lg" style="width:100%" id="loginBtn">Entrar</button>
        ${info.demo_mode ? `<div class="demo-accounts"><h3>Ambiente de demonstração</h3>
          <small>Escolha um perfil para entrar com a conta de teste correspondente.${info.ephemeral_database ? ' Os dados são temporários e voltam ao estado inicial quando o servidor reinicia.' : ''}</small>
          ${(info.demo_accounts || []).map((a) => `<button type="button" class="demo-btn" data-u="${esc(a.username)}" data-p="${esc(a.password)}"><span class="avatar">${initials(ROLE_LABEL[a.role])}</span><span><b>${esc(ROLE_LABEL[a.role])}</b><small>${esc(a.description)}</small></span></button>`).join('')}
        </div>` : ''}
      </form></section></div>`;
    const form = $('#loginForm');
    const doLogin = async (u, p) => {
      $('#loginErr').innerHTML = '';
      await withLoading($('#loginBtn'), async () => {
        try {
          const r = await api('/auth/login', { method: 'POST', body: { username: u, password: p } });
          S.token = r.access_token; S.user = r.user;
          sessionStorage.setItem('cs_token', S.token);
          location.hash = '';
          await this.enter();
        } catch (e) { $('#loginErr').innerHTML = notice('bad', 'Não foi possível entrar', esc(e.message)); }
      });
    };
    form.addEventListener('submit', (e) => { e.preventDefault(); doLogin($('#lu').value.trim(), $('#lp').value); });
    $$('.demo-btn').forEach((b) => b.addEventListener('click', () => { $('#lu').value = b.dataset.u; $('#lp').value = b.dataset.p; doLogin(b.dataset.u, b.dataset.p); }));
    $('#lu').focus();
  },

  sessionExpired() {
    S.token = null; S.user = null; sessionStorage.removeItem('cs_token'); closeOverlay();
    this.renderLogin('Sua sessão terminou. Entre novamente para continuar.');
  },

  async logout() {
    try { await api('/auth/logout', { method: 'POST' }); } catch (_) { /* segue */ }
    S.token = null; S.user = null; sessionStorage.removeItem('cs_token'); location.hash = '';
    this.renderLogin();
  },

  /* -------------------------------------------------------------- estrutura */
  async enter() {
    await this.loadCampaigns();
    const saved = sessionStorage.getItem('cs_campaign');
    const active = S.campaigns.find((c) => c.status === 'ATIVA');
    S.campaignId = S.campaigns.some((c) => String(c.id) === saved) ? saved : (active || S.campaigns[0] || {}).id || null;
    this.renderShell();
    this.route();
  },

  async loadCampaigns() {
    try { S.campaigns = await api('/campaigns'); } catch (_) { S.campaigns = []; }
  },

  renderShell() {
    const u = S.user;
    const info = S.info || {};
    const nav = NAV.map((g) => {
      const items = g.items.filter((i) => i.roles.includes(u.role));
      if (!items.length) return '';
      return `<div class="nav-group"><span>${esc(g.group)}</span>${items.map((i) => `<a href="#/${i.key}" data-key="${i.key}" title="${esc(i.label)}">${icon(i.icon)}<span>${esc(i.label)}</span></a>`).join('')}</div>`;
    }).join('');
    $('#root').innerHTML = `<div class="shell ${localStorage.getItem('cs_collapsed') === '1' ? 'collapsed' : ''}" id="shell">
      <aside class="sidebar" aria-label="Menu principal">
        <div class="brand-mark"><span class="brand-logo">${icon('talao', 'ic-lg')}</span><span class="t">Campanhas e Sorteios<small>Complexo Comercial de Barcarena</small></span></div>
        <nav class="nav">${nav}</nav>
        <div class="side-user"><span class="avatar">${esc(initials(u.full_name))}</span><span class="t"><b>${esc(u.full_name)}</b>${esc(ROLE_LABEL[u.role])}</span>
          <button class="icon-btn" id="btnPwd" title="Trocar senha" aria-label="Trocar senha">${icon('cadeado')}</button>
          <button class="icon-btn" id="btnLogout" title="Sair" aria-label="Sair">${icon('sair')}</button></div>
      </aside>
      <div class="main">
        ${info.demo_mode ? `<div class="demo-banner">${icon('info')}<span><b>Ambiente de demonstração.</b> ${info.ephemeral_database ? 'Os dados são temporários e podem ser reiniciados a qualquer momento.' : 'As contas de teste estão habilitadas.'} Não use dados reais de consumidores.</span></div>` : ''}
        <header class="topbar">
          <button class="icon-btn mobile-menu" id="btnMenu" aria-label="Abrir menu">${icon('menu')}</button>
          <button class="icon-btn collapse-btn" id="btnCollapse" aria-label="Recolher menu" title="Recolher menu">${icon('recolher')}</button>
          <strong id="topTitle"></strong>
          <div class="ctx" id="ctxCampaign" hidden><label for="ctxSel">Campanha</label><select id="ctxSel"></select></div>
        </header>
        <main class="content" id="view" tabindex="-1"></main>
      </div></div>`;
    $('#btnLogout').onclick = () => this.logout();
    $('#btnPwd').onclick = () => this.changePassword();
    $('#btnCollapse').onclick = () => { const s = $('#shell'); s.classList.toggle('collapsed'); localStorage.setItem('cs_collapsed', s.classList.contains('collapsed') ? '1' : '0'); };
    $('#btnMenu').onclick = () => $('#shell').classList.toggle('menu-open');
    $('#ctxSel').onchange = (e) => { S.campaignId = e.target.value; sessionStorage.setItem('cs_campaign', S.campaignId); this.route(); };
  },

  refreshCampaignSelect() {
    const sel = $('#ctxSel');
    if (!sel) return;
    sel.innerHTML = S.campaigns.length ? campaignOptions(S.campaignId) : '<option value="">Nenhuma campanha</option>';
  },

  route() {
    const u = S.user;
    let [key, ...rest] = (location.hash.replace(/^#\/?/, '') || HOME[u.role]).split('/');
    const allowed = NAV.flatMap((g) => g.items).filter((i) => i.roles.includes(u.role)).map((i) => i.key);
    if (!allowed.includes(key)) key = HOME[u.role];
    $$('.nav a').forEach((a) => a.classList.toggle('active', a.dataset.key === key));
    $('#shell').classList.remove('menu-open');
    const item = NAV.flatMap((g) => g.items).find((i) => i.key === key && i.roles.includes(u.role));
    $('#topTitle').textContent = item ? item.label : '';
    $('#ctxCampaign').hidden = !USES_CAMPAIGN.has(key);
    this.refreshCampaignSelect();
    const view = $('#view');
    view.innerHTML = loadingBlock(4);
    view.focus({ preventScroll: true });
    window.scrollTo(0, 0);
    Promise.resolve(Pages[key](view, rest)).catch((e) => {
      if (e.status !== 401) view.innerHTML = errorBlock(e);
    });
  },

  changePassword() {
    if (S.user.is_demo) { toast('Contas de demonstração não podem ter a senha alterada.', 'warn'); return; }
    const body = openDrawer('Trocar senha', `<form id="pf"><div class="field"><label for="p1">Senha atual</label><input id="p1" type="password" required autocomplete="current-password"></div>
      <div class="field"><label for="p2">Nova senha</label><input id="p2" type="password" minlength="8" required autocomplete="new-password"><div class="hint">Mínimo de 8 caracteres. Você precisará entrar de novo.</div></div>
      <button class="btn btn-primary">Salvar nova senha</button></form>`, { modal: true });
    $('#pf', body).onsubmit = async (e) => {
      e.preventDefault();
      try {
        await api('/auth/password', { method: 'POST', body: { current_password: $('#p1').value, new_password: $('#p2').value } });
        closeOverlay(); toast('Senha alterada. Entre novamente.'); this.sessionExpired();
      } catch (err) { fail(err); }
    };
  },
};

document.addEventListener('DOMContentLoaded', () => App.start());
