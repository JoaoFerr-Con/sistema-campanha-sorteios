/* Telas do sistema. Cada função recebe o contêiner da página e monta o conteúdo a partir da API. */
'use strict';

const Pages = {};
const COLORS = { used: '#0f7b6c', issued: '#5fb3a6', distributed: '#9cc9e8', incidents: '#c2412d', vacant: '#b8c4cb', pending: '#f2b705', reg: '#d99a3a', none: '#e5eaed' };

/* ================================================================== PAINEL */
Pages.painel = async (root) => {
  const isAdmin = S.user.role === 'ADMIN';
  const today = new Date().toISOString().slice(0, 10);
  root.innerHTML = `${pageHead('Painel', 'Situação das campanhas, dos comprovantes e do atendimento. Todos os números vêm do banco de dados no momento da consulta.')}
    <div class="filters" id="pf">
      <div class="field"><label for="fFrom">De</label><input type="date" id="fFrom" max="${today}"></div>
      <div class="field"><label for="fTo">Até</label><input type="date" id="fTo" max="${today}"></div>
      <button class="btn btn-secondary" id="fApply">Aplicar período</button>
      <button class="btn btn-ghost" id="fClear">Limpar</button>
    </div><div id="kp">${loadingBlock(5)}</div>`;
  const load = async () => {
    const qs = new URLSearchParams();
    if (S.campaignId) qs.set('campaign_id', S.campaignId);
    if ($('#fFrom').value) qs.set('date_from', $('#fFrom').value);
    if ($('#fTo').value) qs.set('date_to', $('#fTo').value);
    const box = $('#kp');
    try {
      const k = await api(`/reports/kpis?${qs}`);
      const camp = currentCampaign();
      const v = k.vouchers;
      const b = k.boxes;
      const noBoxes = 368 - b.total_cataloged;
      box.innerHTML = `
        ${camp ? `<p class="muted" style="margin-top:-6px">Indicadores de comprovantes e participações filtrados pela campanha <b>${esc(camp.name)}</b>. Troque a campanha no topo da tela.</p>` : ''}
        <div class="stats">
          <div class="stat"><div class="v">${fmtN(k.participations.total_validated)}</div><div class="l">Participações validadas</div><div class="s">números da sorte emitidos</div></div>
          <div class="stat"><div class="v">${fmtN(k.participations.unique_consumers)}</div><div class="l">Consumidores únicos</div><div class="s">por CPF</div></div>
          <div class="stat"><div class="v">${k.vouchers.conversion_pct === null ? '—' : k.vouchers.conversion_pct.toLocaleString('pt-BR') + '%'}</div><div class="l">Conversão</div><div class="s">comprovantes que viraram participação</div></div>
          <div class="stat"><div class="v">${fmtN(k.validation_attempts.rejected)}</div><div class="l">Recusas no balcão</div><div class="s">${fmtN(k.validation_attempts.successful)} validações aceitas</div></div>
          <div class="stat"><div class="v">${fmtN(k.permissionarios.active)}</div><div class="l">Permissionários ativos</div><div class="s">de ${fmtN(k.permissionarios.total)} cadastrados</div></div>
        </div>
        <div class="grid g2">
          <section class="panel"><div class="panel-head"><div><h2>Comprovantes</h2><p>${fmtN(v.total)} gerados em talões</p></div></div>
            ${v.total ? stackBar([
              { label: 'Utilizados', value: v.used_validated, color: COLORS.used },
              { label: 'Emitidos pelo box', value: v.issued, color: COLORS.issued },
              { label: 'Disponíveis no box', value: v.distributed, color: COLORS.distributed },
              { label: 'Ocorrências', value: v.incidents, color: COLORS.incidents }]) : emptyState('Nenhum talão distribuído.', isAdmin ? 'Distribua talões em Talões e comprovantes.' : '')}
          </section>
          <section class="panel"><div class="panel-head"><div><h2>Boxes do complexo</h2><p>368 posições no mapa oficial</p></div>${isAdmin ? '<a class="btn btn-ghost btn-sm" href="#/permissionarios">Ver mapa</a>' : ''}</div>
            ${stackBar([
              { label: 'Confirmados', value: b.confirmed_active, color: COLORS.used },
              { label: 'Vagos', value: b.confirmed_vacant, color: COLORS.vacant },
              { label: 'Em regularização', value: b.under_regularization, color: COLORS.reg },
              { label: 'Sem cadastro oficial', value: Math.max(noBoxes, 0), color: COLORS.none }])}
            ${noBoxes > 0 && isAdmin ? `<p class="muted" style="margin-top:10px;font-size:13.5px">${fmtN(noBoxes)} boxes ainda não passaram pela conferência da planilha. Só boxes confirmados recebem talões.</p>` : ''}
          </section>
        </div>
        <div class="grid g2" style="margin-top:16px">
          <section class="panel"><div class="panel-head"><h2>Participações por dia</h2></div>${byDay(k.participations.by_day)}</section>
          <section class="panel"><div class="panel-head"><h2>Por atividade comercial</h2></div>${hbars(k.participations.by_activity.slice(0, 8), 'activity', 'participations')}</section>
        </div>
        <div class="grid g3" style="margin-top:16px">
          <section class="panel"><div class="panel-head"><h2>Boxes com mais participações</h2></div>
            ${k.participations.by_permissionario.length ? `<table><tbody>${k.participations.by_permissionario.map((r) => `<tr><td><b>Box ${esc(r.box)}</b><span class="sub">${esc(r.permissionario)}</span></td><td class="r num"><b>${fmtN(r.participations)}</b></td></tr>`).join('')}</tbody></table>` : emptyState('Sem participações ainda.')}
          </section>
          <section class="panel"><div class="panel-head"><h2>Motivos de recusa</h2></div>
            ${k.validation_attempts.rejections_breakdown.length ? `<table><tbody>${k.validation_attempts.rejections_breakdown.map((r) => `<tr><td>${esc(r.reason)}</td><td class="r num"><b>${fmtN(r.count)}</b></td></tr>`).join('')}</tbody></table>` : emptyState('Nenhuma recusa registrada.')}
          </section>
          <section class="panel"><div class="panel-head"><h2>Próximos prazos</h2></div>
            ${k.upcoming.length ? `<ul class="timeline">${k.upcoming.map((u) => `<li><b>${fmtDate(u.date)}</b> — ${esc(u.event)}<small>${esc(u.campaign)}</small></li>`).join('')}</ul>` : emptyState('Nenhum prazo futuro.')}
          </section>
        </div>
        ${isAdmin ? `<section class="panel" style="margin-top:16px"><div class="panel-head"><h2>Campanhas</h2><a class="btn btn-ghost btn-sm" href="#/campanhas">Gerenciar</a></div>
          <div class="legend" style="margin:0">${[['ATIVA', k.campaigns.active], ['EM_ELABORACAO', k.campaigns.draft], ['AGUARDANDO_APROVACAO', k.campaigns.awaiting_approval], ['APROVADA', k.campaigns.approved], ['ENCERRADA', k.campaigns.closed]].map(([s, n]) => `<span>${chip(s)} <b class="num">${fmtN(n)}</b></span>`).join('')}</div></section>` : ''}`;
    } catch (e) { box.innerHTML = errorBlock(e); }
  };
  $('#fApply').onclick = load;
  $('#fClear').onclick = () => { $('#fFrom').value = ''; $('#fTo').value = ''; load(); };
  await load();
};
function byDay(rows) {
  if (!rows.length) return emptyState('Sem participações no período.');
  const max = Math.max(...rows.map((r) => r.participations)) || 1;
  return `<div class="vbars">${rows.map((r) => `<div style="height:${(100 * r.participations) / max}%" title="${fmtDate(r.day + 'T12:00:00')}: ${r.participations}"></div>`).join('')}</div>
    <div class="vbars-x"><span>${fmtDate(rows[0].day + 'T12:00:00')}</span><span>${fmtDate(rows[rows.length - 1].day + 'T12:00:00')}</span></div>`;
}

/* ================================================================== BALCÃO */
Pages.balcao = async (root) => {
  const camp = currentCampaign();
  const active = camp && camp.status === 'ATIVA';
  root.innerHTML = `${pageHead('Balcão de atendimento', 'Leia o comprovante, identifique o consumidor e gere o número da sorte. Cada comprovante vale um único número.')}
    ${howto('Como atender', [
      'Confira se a campanha certa está selecionada no topo da tela.',
      'Leia o QR Code ou o código de barras do comprovante com o leitor — ou digite o código (ex.: NATAL-00001) e tecle Enter.',
      'Se o sistema indicar <b>comprovante válido</b>, informe o CPF. Consumidores já cadastrados têm os dados preenchidos automaticamente.',
      'Confirme nome e telefone, marque o consentimento e clique em <b>Validar e gerar número</b>.',
      'Entregue o número da sorte ao consumidor (pode imprimir). O campo do código volta a ficar pronto para o próximo atendimento.'])}
    ${!camp ? notice('warn', 'Nenhuma campanha disponível', 'Peça ao gestor para ativar uma campanha.') : !active ? notice('warn', 'Campanha não está ativa', `A campanha selecionada está <b>${esc(statusLabel(camp.status))}</b>. Selecione uma campanha ativa no topo para validar comprovantes.`) : ''}
    <div class="grid g-side">
      <section class="panel">
        <form id="attForm" autocomplete="off" novalidate>
          <div class="field"><label for="code">Código do comprovante</label>
            <div class="inline-form"><div class="field" style="flex:3"><input id="code" class="scan-input" placeholder="NATAL-00001" ${active ? '' : 'disabled'} aria-describedby="codeCheck"></div>
            ${'BarcodeDetector' in window ? `<button type="button" class="btn btn-secondary btn-lg" id="btnCam" title="Ler com a câmera">${icon('camera')}<span>Câmera</span></button>` : ''}</div>
            <div class="check-line" id="codeCheck" aria-live="polite"><span class="muted" style="font-weight:400">Aguardando leitura do comprovante.</span></div>
          </div>
          <hr class="divider">
          <div class="row">
            <div class="field"><label for="cpf">CPF do consumidor</label><input id="cpf" inputmode="numeric" placeholder="000.000.000-00" required><div class="hint" id="cpfHint"></div></div>
            <div class="field"><label for="phone">Telefone com DDD</label><input id="phone" inputmode="tel" placeholder="(91) 98000-0000" required></div>
          </div>
          <div class="field"><label for="name">Nome completo</label><input id="name" required autocomplete="off"></div>
          <div class="row">
            <div class="field"><label for="bairro">Bairro <small>(opcional)</small></label><input id="bairro" placeholder="Ex.: Vila dos Cabanos"></div>
            <div class="field"><label for="email">E-mail <small>(opcional)</small></label><input id="email" type="email"></div>
          </div>
          <label class="check" style="margin-bottom:16px"><input type="checkbox" id="consent" checked><span>O consumidor autoriza o uso dos dados para esta campanha e para contato em caso de premiação, conforme o regulamento (LGPD).</span></label>
          <button class="btn btn-primary btn-lg" id="btnValidate" style="width:100%" ${active ? '' : 'disabled'}>${icon('ok')}Validar e gerar número</button>
        </form>
      </section>
      <section>
        <div id="result"><div class="ticket-empty">${icon('talao', 'ic-lg')}<p style="margin:8px 0 0">O número da sorte aparece aqui depois da validação.</p></div></div>
        <section class="panel" style="margin-top:16px"><div class="panel-head"><h2>Minhas últimas validações</h2><button class="btn btn-ghost btn-sm" id="btnHist">Atualizar</button></div><div id="hist">${loadingBlock(3)}</div></section>
      </section>
    </div>`;
  const code = $('#code'), cpf = $('#cpf'), check = $('#codeCheck');
  maskCpfInput(cpf); maskPhoneInput($('#phone'));
  let lastCheck = null;

  const runCheck = async () => {
    const v = code.value.trim();
    if (!v || !camp) { check.className = 'check-line'; check.innerHTML = '<span class="muted" style="font-weight:400">Aguardando leitura do comprovante.</span>'; lastCheck = null; return; }
    check.className = 'check-line'; check.innerHTML = '<span class="muted">Consultando…</span>';
    try {
      const r = await api(`/vouchers/eligibility?campaign_id=${camp.id}&code=${encodeURIComponent(v)}`);
      lastCheck = r;
      check.className = `check-line ${r.ok ? 'ok' : 'bad'}`;
      check.innerHTML = `${icon(r.ok ? 'ok' : 'erro')}<span>${esc(r.message)}</span>`;
      if (r.voucher && r.voucher.full_code !== v.toUpperCase()) code.value = r.voucher.full_code;
      return r;
    } catch (e) { check.className = 'check-line warn'; check.innerHTML = `${icon('alerta')}<span>${esc(e.message)}</span>`; }
  };
  const debounced = debounce(runCheck, 450);
  code.addEventListener('input', debounced);
  code.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') { e.preventDefault(); const r = await runCheck(); if (r && r.ok) cpf.focus(); }
  });
  cpf.addEventListener('input', debounce(async () => {
    const raw = cpf.value;
    const hint = $('#cpfHint');
    if (raw.replace(/\D/g, '').length < 11) { hint.textContent = ''; cpf.classList.remove('invalid'); return; }
    if (!cpfValid(raw)) { hint.textContent = 'CPF inválido — confira os números.'; cpf.classList.add('invalid'); return; }
    cpf.classList.remove('invalid');
    try {
      const p = await api(`/attendance/participant?cpf=${encodeURIComponent(raw)}&campaign_id=${camp ? camp.id : ''}`);
      if (p.found) {
        $('#name').value = p.name || ''; $('#phone').value = p.phone || ''; $('#bairro').value = p.neighborhood || ''; $('#email').value = p.email || '';
        hint.textContent = `Consumidor já cadastrado · ${p.numbers_in_campaign} número(s) nesta campanha (limite ${camp ? camp.max_numbers_per_cpf : '—'}).`;
      } else hint.textContent = 'Primeiro cadastro deste CPF.';
    } catch (_) { hint.textContent = ''; }
  }, 300));

  const loadHist = async () => {
    try {
      const rows = await api(`/attendance/attempts?limit=8&mine=true${camp ? `&campaign_id=${camp.id}` : ''}`);
      $('#hist').innerHTML = rows.length ? `<table><tbody>${rows.map((a) => `<tr><td><b>${esc(a.voucher_code)}</b><span class="sub">${fmtDateTime(a.timestamp)} · ${esc(a.participant_cpf)}</span></td>
        <td class="r">${a.success ? `<span class="chip ok">Nº ${esc(a.lucky_number || '')}</span>` : `<span class="chip bad" title="${esc(a.refusal_reason)}">Recusado</span>`}</td></tr>`).join('')}</tbody></table>` : emptyState('Nenhuma validação sua nesta campanha ainda.');
    } catch (e) { $('#hist').innerHTML = errorBlock(e); }
  };
  $('#btnHist').onclick = loadHist;
  loadHist();

  $('#attForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const missing = [];
    if (!code.value.trim()) missing.push('código do comprovante');
    if (!cpfValid(cpf.value)) missing.push('CPF válido');
    if ($('#name').value.trim().length < 3) missing.push('nome');
    if ($('#phone').value.replace(/\D/g, '').length < 10) missing.push('telefone com DDD');
    if (!$('#consent').checked) missing.push('consentimento');
    if (missing.length) { showRefusal('Dados incompletos', `Preencha: ${missing.join(', ')}.`); return; }
    await withLoading($('#btnValidate'), async () => {
      try {
        const r = await api('/attendance/validate', { method: 'POST', body: {
          campaign_id: camp.id, voucher_code: code.value.trim(), participant_cpf: cpf.value, participant_name: $('#name').value.trim(),
          participant_phone: $('#phone').value, participant_neighborhood: $('#bairro').value.trim() || null,
          participant_email: $('#email').value.trim() || null, consent_lgpd: $('#consent').checked } });
        showTicket(r);
        ['code', 'cpf', 'name', 'phone', 'bairro', 'email'].forEach((id) => { $('#' + id).value = ''; });
        $('#cpfHint').textContent = '';
        check.className = 'check-line'; check.innerHTML = '<span class="muted" style="font-weight:400">Pronto para o próximo comprovante.</span>';
        loadHist();
      } catch (err) {
        const title = err.status === 409 ? 'Comprovante já utilizado' : err.status === 0 ? 'Erro de comunicação' : 'Validação recusada';
        showRefusal(title, err.message);
        runCheck(); loadHist();
      } finally { code.focus(); }
    });
  });

  function showTicket(r) {
    $('#result').innerHTML = `<div class="ticket reveal" role="status" aria-live="assertive">
      <div><div class="t-label">Número da sorte</div><div class="t-number">${esc(r.lucky_number)}</div></div>
      <div style="text-align:right"><button class="btn btn-secondary btn-sm" id="btnPrint">${icon('imprimir')}Imprimir</button></div>
      <div class="t-meta"><div>Consumidor<b>${esc(r.participant.name)}</b>${esc(r.participant.cpf_masked)}</div>
      <div>Comprovante<b>${esc(r.voucher.code)}</b>Box ${esc(r.voucher.box_number)}</div>
      <div>Nesta campanha<b>${r.participant.total_tickets_in_campaign} número(s)</b>${fmtDateTime(r.validated_at)}</div></div></div>`;
    $('#btnPrint').onclick = () => {
      $('#printArea').innerHTML = `<div style="max-width:300px;font-size:13px"><b>Complexo Comercial de Barcarena</b><br>${esc(r.campaign.name)}<hr>
        <div style="font-size:12px">Número da sorte</div><div style="font-size:40px;font-weight:800;letter-spacing:.06em">${esc(r.lucky_number)}</div><hr>
        ${esc(r.participant.name)}<br>CPF ${esc(r.participant.cpf_masked)}<br>Comprovante ${esc(r.voucher.code)} · Box ${esc(r.voucher.box_number)}<br>${fmtDateTime(r.validated_at)}<br><br>
        <small>Guarde este comprovante. A apuração segue o regulamento da campanha e a Loteria Federal.</small></div>`;
      window.print();
    };
  }
  function showRefusal(title, text) {
    $('#result').innerHTML = `<div class="refusal" role="alert"><h3>${esc(title)}</h3><p style="margin:0">${esc(text)}</p></div>`;
  }

  if ($('#btnCam')) $('#btnCam').onclick = () => scanWithCamera((txt) => { code.value = txt; runCheck().then((r) => r && r.ok && cpf.focus()); });
  if (active) code.focus();
};

function scanWithCamera(onCode) {
  const body = openDrawer('Ler comprovante com a câmera', `<video id="camv" playsinline style="width:100%;border-radius:8px;background:#000"></video><p class="muted" style="margin-top:8px">Aponte para o QR Code ou código de barras do comprovante.</p>`, { modal: true });
  const video = $('#camv', body);
  let stream, stop = false;
  const detector = new window.BarcodeDetector({ formats: ['qr_code', 'code_128', 'code_39', 'ean_13'] });
  navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }).then((s) => {
    stream = s; video.srcObject = s; video.play();
    const tick = async () => {
      if (stop || !document.body.contains(video)) { stream.getTracks().forEach((t) => t.stop()); return; }
      try { const codes = await detector.detect(video); if (codes.length) { stop = true; stream.getTracks().forEach((t) => t.stop()); closeOverlay(); onCode(codes[0].rawValue); return; } } catch (_) { /* quadro ilegível */ }
      requestAnimationFrame(tick);
    };
    tick();
  }).catch(() => { body.innerHTML = notice('warn', 'Câmera indisponível', 'Permita o acesso à câmera no navegador ou use o leitor/teclado.'); });
}

/* ================================================================== CONSULTA (atendente) */
Pages.consulta = async (root) => {
  root.innerHTML = `${pageHead('Consultar comprovante', 'Veja a origem e a situação de qualquer comprovante antes de atender.')}
    <section class="panel" style="max-width:760px">${voucherSearchHtml()}</section>`;
  bindVoucherSearch(root);
};
function voucherSearchHtml() {
  return `<form class="inline-form" id="vsForm"><div class="field"><label for="vsCode">Código ou QR do comprovante</label><input id="vsCode" placeholder="Ex.: NATAL-00001" autocomplete="off"></div>
    <button class="btn btn-primary">${icon('busca')}Consultar</button></form><div id="vsOut" style="margin-top:16px"></div>`;
}
function bindVoucherSearch(root) {
  $('#vsForm', root).onsubmit = async (e) => {
    e.preventDefault();
    const v = $('#vsCode', root).value.trim();
    const out = $('#vsOut', root);
    if (!v) return;
    out.innerHTML = loadingBlock(3);
    try {
      const d = await api(`/vouchers/lookup/${encodeURIComponent(v)}`);
      const p = d.participation;
      out.innerHTML = `<div class="panel-head"><div><h2>${esc(d.full_code)}</h2><p>${esc(d.campaign_name)}</p></div>${chip(d.status)}</div>
        <dl class="kv"><dt>Box</dt><dd>${esc(d.box_number)} — ${esc(d.permissionario_name)} ${d.permissionario_status !== 'ATIVO' ? chip(d.permissionario_status) : ''}</dd>
        <dt>Lote</dt><dd>#${esc(d.batch_number)} ${d.batch_status === 'CANCELADO' ? chip('CANCELADO', 'Lote cancelado') : ''}</dd>
        <dt>Emissão no box</dt><dd>${d.issued_at ? `${fmtDateTime(d.issued_at)} · ${fmtMoney(d.issued_value)}${d.invoice_doc_number ? ` · ${esc(d.invoice_doc_number)}` : ''}` : 'Ainda não registrada pelo permissionário'}</dd>
        <dt>Participação</dt><dd>${p ? `Número <b>${esc(p.lucky_number)}</b> em ${fmtDateTime(p.validated_at)}<br><small>${esc(p.participant_name)} · ${esc(p.participant_cpf_masked)}${p.attendant ? ` · atendido por ${esc(p.attendant)}` : ''}</small>` : 'Ainda não utilizado'}</dd></dl>
        <div class="qr-box"><img alt="QR Code do comprovante ${esc(d.full_code)}" id="qrImg"><div><b>QR Code do comprovante</b><p class="muted" style="margin:4px 0 0">O leitor do balcão reconhece este código. Use-o para reimprimir etiquetas.</p></div></div>`;
      const res = await api(`/vouchers/${encodeURIComponent(d.full_code)}/qr.svg`, { raw: true });
      $('#qrImg', out).src = URL.createObjectURL(await res.blob());
    } catch (err) { out.innerHTML = err.status === 404 ? notice('bad', 'Comprovante não encontrado', `Confira o código digitado: ${esc(v)}.`) : errorBlock(err); }
  };
}

/* ================================================================== TALÕES E COMPROVANTES */
Pages.comprovantes = async (root) => {
  root.innerHTML = `${pageHead('Talões e comprovantes', 'Distribua lotes numerados aos boxes, acompanhe o uso e faça a prestação de contas.')}
    ${howto('Como distribuir talões', [
      'A campanha precisa estar <b>Aprovada</b> ou <b>Ativa</b>, e o box precisa estar <b>Confirmado</b> na conferência da planilha.',
      'Em <b>Novo lote</b>, escolha o box. O permissionário vinculado é preenchido automaticamente.',
      'Informe o prefixo (ex.: NATAL) e a quantidade. O sistema sugere o próximo número livre para evitar sobreposição.',
      'Acompanhe em <b>Lotes</b> quantos comprovantes foram emitidos, utilizados e quantos têm ocorrência.'])}
    ${tabsHtml([['lotes', 'Lotes'], ['novo', 'Novo lote'], ['consulta', 'Consultar comprovante']], 'lotes')}
    <div id="tabBody"></div>`;
  const body = $('#tabBody');
  const show = (t) => ({ lotes: lotesTab, novo: novoLoteTab, consulta: () => { body.innerHTML = `<section class="panel" style="max-width:760px">${voucherSearchHtml()}</section>`; bindVoucherSearch(body); } })[t](body);
  bindTabs(root, show);
  await lotesTab(body);
};
async function lotesTab(body) {
  body.innerHTML = `<div class="filters"><div class="field"><label for="lq">Buscar</label><input id="lq" placeholder="Box, permissionário ou prefixo"></div>
    <a class="btn btn-secondary" id="expL">${icon('baixar')}Exportar Excel</a></div><div id="lt">${loadingBlock(4)}</div>`;
  const load = async () => {
    const qs = new URLSearchParams();
    if (S.campaignId) qs.set('campaign_id', S.campaignId);
    if ($('#lq').value.trim()) qs.set('q', $('#lq').value.trim());
    try {
      const rows = await api(`/vouchers/batches?${qs}`);
      $('#lt').innerHTML = rows.length ? `<div class="table-wrap"><table><thead><tr><th>Lote</th><th>Box / permissionário</th><th>Intervalo</th><th class="r">Total</th><th>Uso</th><th class="r">Disponíveis</th><th class="r">Ocorrências</th><th>Situação</th><th></th></tr></thead><tbody>
        ${rows.map((b) => `<tr><td><b>#${b.batch_number}</b><span class="sub">${fmtDate(b.distributed_at)}</span></td><td><b>Box ${esc(b.box_number)}</b><span class="sub">${esc(b.permissionario_name)}</span></td>
        <td class="num">${esc(b.first_code)}<span class="sub">até ${esc(b.last_code)}</span></td><td class="r num">${fmtN(b.total)}</td>
        <td><div class="progress" title="${b.used} utilizados de ${b.total}"><b style="width:${(100 * b.used) / b.total}%"></b></div><span class="sub">${fmtN(b.used)} utilizados · ${fmtN(b.issued)} emitidos</span></td>
        <td class="r num">${fmtN(b.available)}</td><td class="r num">${b.incidents ? `<b style="color:var(--bad)">${b.incidents}</b>` : '0'}</td><td>${chip(b.status === 'ATIVO' ? 'ATIVO' : b.status)}</td>
        <td class="r"><button class="btn btn-ghost btn-sm" data-b="${b.id}">Detalhes</button></td></tr>`).join('')}</tbody></table></div>`
        : emptyState('Nenhum lote nesta campanha.', 'Use a aba Novo lote para distribuir o primeiro talão.');
      $$('[data-b]', body).forEach((btn) => btn.onclick = () => batchDrawer(rows.find((r) => String(r.id) === btn.dataset.b), load));
    } catch (e) { $('#lt').innerHTML = errorBlock(e); }
  };
  $('#lq').addEventListener('input', debounce(load, 350));
  $('#expL').onclick = () => downloadFile(`/reports/export/lotes.xlsx${S.campaignId ? `?campaign_id=${S.campaignId}` : ''}`, 'lotes.xlsx').catch(fail);
  await load();
}
async function batchDrawer(b, reload) {
  const body = openDrawer(`Lote #${b.batch_number} — Box ${b.box_number}`, loadingBlock(5), { subtitle: esc(b.permissionario_name) });
  try {
    const [hist, vouchers] = await Promise.all([api(`/vouchers/batches/${b.id}/history`), api(`/vouchers/batches/${b.id}/vouchers`)]);
    body.innerHTML = `<dl class="kv"><dt>Campanha</dt><dd>${esc(b.campaign_name)}</dd><dt>Intervalo</dt><dd>${esc(b.first_code)} a ${esc(b.last_code)}</dd>
      <dt>Distribuído</dt><dd>${fmtDateTime(b.distributed_at)} por ${esc(b.distributed_by)}</dd><dt>Situação</dt><dd>${chip(b.status)}</dd>
      ${b.cancel_reason ? `<dt>Motivo do cancelamento</dt><dd>${esc(b.cancel_reason)}</dd>` : ''}${b.notes ? `<dt>Observações</dt><dd>${esc(b.notes)}</dd>` : ''}</dl>
      <hr class="divider"><h3>Prestação de contas</h3>
      ${stackBar([{ label: 'Utilizados', value: b.used, color: COLORS.used }, { label: 'Emitidos', value: b.issued, color: COLORS.issued }, { label: 'No box', value: b.available - b.issued, color: COLORS.distributed }, { label: 'Ocorrências', value: b.incidents, color: COLORS.incidents }])}
      <hr class="divider"><h3>Comprovantes</h3>
      <div class="table-wrap" style="max-height:260px;overflow:auto;margin-top:8px"><table><tbody>${vouchers.map((v) => `<tr><td class="num">${esc(v.code)}</td><td>${chip(v.status)}</td><td class="r num">${v.lucky_number ? 'Nº ' + esc(v.lucky_number) : ''}</td></tr>`).join('')}</tbody></table></div>
      <hr class="divider"><h3>Movimentações</h3>
      ${hist.length ? `<ul class="timeline">${hist.slice(-30).reverse().map((h) => `<li><b>${esc(actionText(h.action))}</b><small>${fmtDateTime(h.timestamp)} · ${esc(h.username)}${h.after && h.after.voucher_code ? ` · ${esc(h.after.voucher_code)}` : h.after && h.after.code ? ` · ${esc(h.after.code)}` : ''}</small></li>`).join('')}</ul>` : emptyState('Sem movimentações.')}
      ${b.status === 'ATIVO' ? `<hr class="divider"><button class="btn btn-danger" id="btnCancelB">Cancelar lote</button><p class="muted" style="font-size:13px;margin-top:6px">Comprovantes ainda não utilizados ficam cancelados. Os já utilizados continuam válidos.</p>` : ''}`;
    if ($('#btnCancelB', body)) $('#btnCancelB', body).onclick = async () => {
      const reason = await askReason({ title: `Cancelar lote #${b.batch_number}`, text: 'Esta ação não pode ser desfeita.', confirm: 'Cancelar lote', danger: true });
      if (!reason) return;
      try { const r = await api(`/vouchers/batches/${b.id}/cancel`, { method: 'POST', body: { reason } }); toast(`Lote cancelado: ${r.vouchers_cancelled} comprovantes cancelados.`); reload(); } catch (e) { fail(e); }
    };
  } catch (e) { body.innerHTML = errorBlock(e); }
}
const ACTION_TXT = { BATCH_CREATED: 'Lote distribuído', BATCH_CANCELLED: 'Lote cancelado', VOUCHER_ISSUED_BY_MERCHANT: 'Emitido pelo box', PARTICIPATION_VALIDATED: 'Validado no balcão', VOUCHER_INCIDENT_EXTRAVIADO: 'Registrado como extraviado', VOUCHER_INCIDENT_DEVOLVIDO: 'Registrado como devolvido', VOUCHER_INCIDENT_CANCELADO: 'Cancelado pelo box' };
const actionText = (a) => ACTION_TXT[a] || a;

async function novoLoteTab(body) {
  const camp = currentCampaign();
  if (!camp || !['APROVADA', 'ATIVA'].includes(camp.status)) {
    body.innerHTML = notice('warn', 'Selecione uma campanha aprovada ou ativa', 'Talões só podem ser distribuídos para campanhas aprovadas ou ativas. Troque a campanha no topo da tela.');
    return;
  }
  body.innerHTML = loadingBlock(4);
  const boxes = await api('/boxes?status=CONFIRMADO');
  const usable = boxes.filter((b) => b.permissionario_id && b.permissionario_status === 'ATIVO');
  body.innerHTML = `<section class="panel" style="max-width:720px"><div class="panel-head"><div><h2>Novo lote para ${esc(camp.name)}</h2><p>${fmtN(usable.length)} boxes confirmados com permissionário ativo.</p></div></div>
    ${usable.length ? '' : notice('warn', 'Nenhum box apto', 'Confirme boxes na conferência da planilha (Permissionários e boxes).')}
    <form id="nl"><div class="field"><label for="nlBox">Box</label><select id="nlBox" required><option value="">Selecione…</option>${usable.map((b) => `<option value="${b.id}" data-p="${b.permissionario_id}" data-n="${esc(b.permissionario)}">Box ${esc(b.box_number)} — ${esc(b.permissionario)} (${esc(b.activity || '')})</option>`).join('')}</select></div>
    <div class="field"><label>Permissionário</label><input id="nlPerm" readonly placeholder="Preenchido ao escolher o box"></div>
    <div class="row"><div class="field"><label for="nlPrefix">Prefixo</label><input id="nlPrefix" required maxlength="10" value="${esc((camp.name.match(/[A-Za-z]{3,}/) || ['CAMP'])[0].toUpperCase().slice(0, 8))}"><div class="hint">2 a 10 letras ou números.</div></div>
    <div class="field"><label for="nlStart">Primeiro número</label><input id="nlStart" type="number" min="1" max="99999" required></div>
    <div class="field"><label for="nlQty">Quantidade</label><input id="nlQty" type="number" min="1" max="5000" value="50" required></div></div>
    <p class="muted" id="nlPreview"></p>
    <div class="field"><label for="nlNotes">Observações <small>(opcional)</small></label><input id="nlNotes"></div>
    <button class="btn btn-primary" id="nlBtn">${icon('mais')}Distribuir lote</button></form></section>`;
  const prefix = $('#nlPrefix'), start = $('#nlStart'), qty = $('#nlQty');
  const preview = () => {
    const p = prefix.value.trim().toUpperCase(), s = +start.value, q = +qty.value;
    $('#nlPreview').textContent = p && s && q ? `Serão gerados ${fmtN(q)} comprovantes: ${p}-${String(s).padStart(5, '0')} a ${p}-${String(s + q - 1).padStart(5, '0')}.` : '';
  };
  const suggest = async () => {
    if (!prefix.value.trim()) return;
    try { const r = await api(`/vouchers/batches/next-range?prefix=${encodeURIComponent(prefix.value.trim())}`); start.value = r.next_start; preview(); } catch (_) { /* ignora */ }
  };
  $('#nlBox').onchange = (e) => { const o = e.target.selectedOptions[0]; $('#nlPerm').value = o && o.dataset.n ? o.dataset.n : ''; };
  prefix.addEventListener('input', debounce(suggest, 300));
  [start, qty].forEach((el) => el.addEventListener('input', preview));
  await suggest();
  $('#nl').onsubmit = async (e) => {
    e.preventDefault();
    const o = $('#nlBox').selectedOptions[0];
    if (!o || !o.value) { toast('Escolha o box.', 'warn'); return; }
    await withLoading($('#nlBtn'), async () => {
      try {
        const s = +start.value;
        const r = await api('/vouchers/batches', { method: 'POST', body: { campaign_id: camp.id, box_id: +o.value, permissionario_id: +o.dataset.p, code_prefix: prefix.value.trim(), start_number: s, end_number: s + +qty.value - 1, notes: $('#nlNotes').value.trim() || null } });
        toast(`Lote #${r.batch_number} distribuído com ${r.total_vouchers} comprovantes.`);
        $('.tabs button[data-tab="lotes"]').click();
      } catch (err) { fail(err); }
    });
  };
}

/* ================================================================== CAMPANHAS */
const TRANSITION_BTN = {
  AGUARDANDO_APROVACAO: ['Enviar para aprovação', 'btn-primary'], ATIVA: ['Ativar campanha', 'btn-primary'],
  ENCERRADA: ['Encerrar participações', 'btn-secondary'], EM_ELABORACAO: ['Devolver para elaboração', 'btn-secondary'],
  CANCELADA: ['Cancelar campanha', 'btn-danger'], APROVADA: null,
};
Pages.campanhas = async (root, rest) => {
  if (rest[0] === 'nova') return campaignEditor(root, null);
  if (rest[0]) return campaignDetail(root, rest[0]);
  root.innerHTML = `${pageHead('Campanhas', 'Cada campanha passa por sete etapas, da elaboração à ativação. O sistema mostra o que falta em cada uma.', `<a class="btn btn-primary" href="#/campanhas/nova">${icon('mais')}Nova campanha</a>`)}
    ${howto('Ciclo de vida de uma campanha', [
      '<b>Em elaboração</b>: preencha informações gerais, calendário, regras, prêmios e regulamento.',
      '<b>Enviar para aprovação</b>: só é liberado quando as cinco primeiras etapas estão completas. A campanha deixa de ser editável.',
      '<b>Aprovação jurídica</b>: registre os seis itens obrigatórios e o parecer. Com todos marcados, a campanha fica <b>Aprovada</b> e já pode receber talões.',
      '<b>Ativar</b>: libera o balcão e a emissão de comprovantes pelos boxes.',
      '<b>Encerrar participações</b>: bloqueia novas validações. Em seguida, a apuração congela a base e registra a extração da Loteria Federal.'])}
    <div id="cl">${loadingBlock(4)}</div>`;
  await App.loadCampaigns();
  const list = S.campaigns;
  $('#cl').innerHTML = list.length ? `<div class="table-wrap"><table><thead><tr><th>Campanha</th><th>Situação</th><th>Período de compras</th><th>Etapas</th><th class="r">Números emitidos</th></tr></thead><tbody>
    ${list.map((c) => { const done = c.readiness.filter((s) => s.done).length; return `<tr class="clickable" data-id="${c.id}" tabindex="0"><td><b>${esc(c.name)}</b>${c.is_demo ? '<span class="sub">Demonstração</span>' : ''}</td><td>${chip(c.status)}</td>
      <td>${fmtDate(c.purchase_start_date)} a ${fmtDate(c.purchase_end_date)}</td><td><div class="progress" style="max-width:120px"><b style="width:${(100 * done) / 7}%"></b></div><span class="sub">${done} de 7</span></td><td class="r num">${fmtN(c.lucky_numbers_issued)}</td></tr>`; }).join('')}
    </tbody></table></div>` : emptyState('Nenhuma campanha cadastrada.', 'Crie a primeira campanha para começar.', `<a class="btn btn-primary" href="#/campanhas/nova">Nova campanha</a>`);
  $$('tr[data-id]').forEach((tr) => { const go = () => { location.hash = `#/campanhas/${tr.dataset.id}`; }; tr.onclick = go; tr.onkeydown = (e) => e.key === 'Enter' && go(); });
};

async function getOptions() { if (!S.options) S.options = await api('/campaigns/options'); return S.options; }

function campaignFormHtml(c, editable) {
  const dis = editable ? '' : 'disabled';
  const v = (k) => esc(c ? c[k] ?? '' : '');
  const prizes = c && c.prizes && c.prizes.length ? c.prizes : [{ title: '', estimated_value: '', draw_date: '' }];
  return `<form id="cf">
  <section class="panel" id="st-geral"><h2>Informações gerais</h2><p class="muted">Identificação da campanha e do promotor legal.</p>
    <div class="field"><label for="cName">Nome da campanha</label><input id="cName" value="${v('name')}" required ${dis}></div>
    <div class="field"><label for="cDesc">Descrição e objetivo</label><textarea id="cDesc" ${dis}>${v('description')}</textarea></div>
    <div class="row"><div class="field"><label for="cProm">Promotor legal</label><input id="cProm" value="${v('legal_promoter_name')}" placeholder="Prefeitura Municipal de Barcarena — SEICOMTEC" ${dis}></div>
    <div class="field"><label for="cPromDoc">CNPJ do promotor</label><input id="cPromDoc" value="${v('legal_promoter_doc')}" ${dis}></div></div></section>
  <section class="panel" id="st-periodo"><h2>Período e calendário</h2><p class="muted">O período de compras precisa estar dentro da campanha; o cadastro de comprovantes vai até, no mínimo, o fim das compras.</p>
    <div class="row"><div class="field"><label for="cStart">Início da campanha</label><input type="datetime-local" id="cStart" value="${toLocalInput(c && c.start_date)}" required ${dis}></div>
    <div class="field"><label for="cEnd">Término da campanha</label><input type="datetime-local" id="cEnd" value="${toLocalInput(c && c.end_date)}" required ${dis}></div></div>
    <div class="row"><div class="field"><label for="cPs">Início das compras</label><input type="datetime-local" id="cPs" value="${toLocalInput(c && c.purchase_start_date)}" required ${dis}></div>
    <div class="field"><label for="cPe">Fim das compras</label><input type="datetime-local" id="cPe" value="${toLocalInput(c && c.purchase_end_date)}" required ${dis}></div>
    <div class="field"><label for="cRe">Fim do cadastro de comprovantes</label><input type="datetime-local" id="cRe" value="${toLocalInput(c && c.registration_end_date)}" required ${dis}></div></div></section>
  <section class="panel" id="st-regras"><h2>Regras de participação</h2>
    <div class="row"><div class="field"><label for="cMin">Valor mínimo de compra (R$)</label><input type="number" step="0.01" min="1" id="cMin" value="${c ? c.min_purchase_value : 20}" ${dis}></div>
    <div class="field"><label for="cMax">Máximo de números por CPF</label><input type="number" min="1" id="cMax" value="${c ? c.max_numbers_per_cpf : 50}" ${dis}></div></div>
    <div class="field"><label for="cRule">Regra de apuração quando não houver número idêntico</label><select id="cRule" ${dis}><option value="">Selecione a regra escrita no regulamento…</option>
      ${Object.entries(S.options.approximation_rules).map(([k, t]) => `<option value="${k}" ${c && c.draw_approximation_rule === k ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select>
      <div class="hint">O número apurado é formado pela unidade do 1º ao 5º prêmio da Loteria Federal. Veja o alerta de concentração de chance na tela de Apuração.</div></div></section>
  <section class="panel" id="st-premios"><h2>Premiações</h2><p class="muted">Os prêmios são apurados nesta ordem.</p>
    <div id="prizeRows">${prizes.map((p, i) => prizeRow(p, i, dis)).join('')}</div>
    ${editable ? `<button type="button" class="btn btn-secondary btn-sm" id="addPrize">${icon('mais')}Adicionar prêmio</button>` : ''}</section>
  <section class="panel" id="st-regulamento"><h2>Regulamento e documentação</h2>
    <div class="row"><div class="field"><label for="cReg">Referência do regulamento aprovado</label><input id="cReg" value="${v('regulation_reference')}" placeholder="Ex.: Processo nº 0000/2026 — Certificado SPA/MF" ${dis}></div>
    <div class="field"><label for="cRegUrl">Link do regulamento publicado <small>(opcional)</small></label><input id="cRegUrl" type="url" value="${v('regulation_url')}" ${dis}></div></div>
    <div class="field"><label for="cRegNotes">Observações e documentos pendentes</label><textarea id="cRegNotes" ${dis}>${v('regulation_notes')}</textarea></div></section>
  ${editable ? `<div style="position:sticky;bottom:0;background:var(--bg);padding:12px 0;display:flex;gap:8px"><button class="btn btn-primary" id="cSave">Salvar campanha</button><a class="btn btn-secondary" href="#/campanhas">Voltar</a></div>` : ''}
  </form>`;
}
function prizeRow(p, i, dis = '') {
  return `<div class="row prize-row" style="align-items:end"><div class="field" style="grid-column:span 2"><label>${i + 1}º prêmio</label><input data-k="title" value="${esc(p.title || '')}" placeholder="Ex.: Motocicleta 160 cc 0 km" ${dis}></div>
    <div class="field"><label>Valor estimado (R$)</label><input data-k="estimated_value" type="number" step="0.01" min="0" value="${p.estimated_value ?? ''}" ${dis}></div>
    <div class="field"><label>Data da extração</label><input data-k="draw_date" type="date" value="${p.draw_date ? p.draw_date.slice(0, 10) : ''}" ${dis}></div></div>`;
}
function readCampaignForm() {
  const prizes = $$('.prize-row').map((r) => ({
    title: $('[data-k=title]', r).value.trim(), estimated_value: $('[data-k=estimated_value]', r).value ? +$('[data-k=estimated_value]', r).value : null,
    draw_date: $('[data-k=draw_date]', r).value ? `${$('[data-k=draw_date]', r).value}T22:00:00` : null,
  })).filter((p) => p.title);
  return {
    name: $('#cName').value.trim(), description: $('#cDesc').value.trim() || null, legal_promoter_name: $('#cProm').value.trim() || null,
    legal_promoter_doc: $('#cPromDoc').value.trim() || null, start_date: fromLocalInput($('#cStart').value), end_date: fromLocalInput($('#cEnd').value),
    purchase_start_date: fromLocalInput($('#cPs').value), purchase_end_date: fromLocalInput($('#cPe').value), registration_end_date: fromLocalInput($('#cRe').value),
    min_purchase_value: +$('#cMin').value, max_numbers_per_cpf: +$('#cMax').value, draw_approximation_rule: $('#cRule').value || null,
    regulation_reference: $('#cReg').value.trim() || null, regulation_url: $('#cRegUrl').value.trim() || null, regulation_notes: $('#cRegNotes').value.trim() || null,
    prizes,
  };
}
function bindCampaignForm(root, c) {
  if ($('#addPrize', root)) $('#addPrize', root).onclick = () => { const n = $$('.prize-row').length; $('#prizeRows').insertAdjacentHTML('beforeend', prizeRow({}, n)); };
  $('#cf', root).onsubmit = async (e) => {
    e.preventDefault();
    const data = readCampaignForm();
    if (!data.start_date || !data.end_date || !data.purchase_start_date || !data.purchase_end_date || !data.registration_end_date) { toast('Preencha todas as datas do calendário.', 'warn'); $('#st-periodo').scrollIntoView({ behavior: 'smooth' }); return; }
    await withLoading($('#cSave'), async () => {
      try {
        if (c) { await api(`/campaigns/${c.id}`, { method: 'PUT', body: data }); toast('Campanha salva.'); await App.loadCampaigns(); campaignDetail(root, c.id); }
        else { const r = await api('/campaigns', { method: 'POST', body: data }); toast('Campanha criada em elaboração.'); await App.loadCampaigns(); location.hash = `#/campanhas/${r.campaign_id}`; }
      } catch (err) { fail(err); }
    });
  };
}
async function campaignEditor(root) {
  await getOptions();
  const now = new Date(); const d = (days) => new Date(now.getTime() + days * 864e5).toISOString();
  const draft = { start_date: d(7), end_date: d(67), purchase_start_date: d(7), purchase_end_date: d(57), registration_end_date: d(60), min_purchase_value: 20, max_numbers_per_cpf: 50, prizes: [] };
  root.innerHTML = `${pageHead('Nova campanha', 'Preencha o que já souber. Você pode salvar e completar depois — a campanha fica em elaboração.')}${campaignFormHtml(draft, true)}`;
  bindCampaignForm(root, null);
  $('#cName').focus();
}

async function campaignDetail(root, id) {
  await getOptions();
  const c = await api(`/campaigns/${id}`);
  const editable = c.status === 'EM_ELABORACAO';
  const firstPending = c.readiness.find((s) => !s.done);
  const actions = c.allowed_transitions.filter((t) => TRANSITION_BTN[t]).map((t) => `<button class="btn ${TRANSITION_BTN[t][1]}" data-tr="${t}">${esc(TRANSITION_BTN[t][0])}</button>`).join('');
  root.innerHTML = `${pageHead(c.name, `${chip(c.status)} ${c.is_demo ? '<span class="chip info">Demonstração</span>' : ''}`, actions)}
    <div class="grid" style="grid-template-columns:minmax(220px,280px) minmax(0,1fr);align-items:start" id="cdGrid">
      <aside class="panel" style="position:sticky;top:76px"><h3 style="margin-bottom:14px">Etapas</h3><ol class="steps">
        ${c.readiness.map((s) => `<li class="${s.done ? 'done' : s === firstPending ? 'current' : ''}"><button data-go="st-${s.key}"><b>${esc(s.title)}</b>${s.done ? '<small>Concluída</small>' : `<small>${esc(s.missing.slice(0, 2).join('; '))}${s.missing.length > 2 ? '…' : ''}</small>`}</button></li>`).join('')}
      </ol></aside>
      <div style="min-width:0">${tabsHtml([['config', 'Configuração'], ['ind', 'Indicadores'], ['lotes', 'Talões'], ['hist', 'Histórico']], 'config')}<div id="cdBody"></div></div>
    </div>`;
  if (window.matchMedia('(max-width: 1100px)').matches) $('#cdGrid').style.gridTemplateColumns = '1fr';
  const body = $('#cdBody');
  const config = () => {
    body.innerHTML = `${!editable ? notice('info', 'Campanha bloqueada para edição', c.status === 'AGUARDANDO_APROVACAO' || c.status === 'APROVADA' ? 'Para alterar dados, devolva a campanha para elaboração. A aprovação jurídica precisará ser refeita.' : 'Campanhas ativas, encerradas ou canceladas não podem ser alteradas.') : ''}
      ${campaignFormHtml(c, editable)}<section class="panel" id="st-juridico" style="margin-top:16px">${legalHtml(c)}</section>
      <section class="panel" id="st-ativacao" style="margin-top:16px"><h2>Publicação e ativação</h2>
      <dl class="kv" style="margin-top:10px"><dt>Aprovada em</dt><dd>${fmtDateTime(c.approved_at)}</dd><dt>Ativada em</dt><dd>${fmtDateTime(c.activated_at)}</dd><dt>Encerrada em</dt><dd>${fmtDateTime(c.closed_at)}</dd><dt>Números emitidos</dt><dd>${fmtN(c.lucky_numbers_issued)}</dd></dl></section>`;
    bindCampaignForm(body, c);
    bindLegal(body, c);
  };
  const show = (t) => {
    if (t === 'config') return config();
    if (t === 'ind') { const k = c.indicators; body.innerHTML = `<div class="stats"><div class="stat"><div class="v">${fmtN(k.participations.total_validated)}</div><div class="l">Participações</div></div><div class="stat"><div class="v">${fmtN(k.participations.unique_consumers)}</div><div class="l">Consumidores únicos</div></div><div class="stat"><div class="v">${fmtN(k.vouchers.total)}</div><div class="l">Comprovantes em talões</div></div><div class="stat"><div class="v">${fmtN(k.validation_attempts.rejected)}</div><div class="l">Recusas</div></div></div>
      <div class="grid g2"><section class="panel"><h2 style="margin-bottom:12px">Por atividade</h2>${hbars(k.participations.by_activity, 'activity', 'participations')}</section><section class="panel"><h2 style="margin-bottom:12px">Por dia</h2>${byDay(k.participations.by_day)}</section></div>`; return; }
    if (t === 'lotes') { S.campaignId = c.id; sessionStorage.setItem('cs_campaign', c.id); return lotesTab(body); }
    if (t === 'hist') return auditList(body, { campaign_id: c.id });
  };
  bindTabs(root, show);
  config();
  $$('[data-go]').forEach((b) => b.onclick = () => { const t = $('.tabs button[data-tab="config"]'); if (!t.classList.contains('active')) t.click(); setTimeout(() => { const el = document.getElementById(b.dataset.go); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 30); });
  $$('[data-tr]').forEach((b) => b.onclick = async () => {
    const target = b.dataset.tr;
    let justification = null;
    if (target === 'CANCELADA' || (target === 'EM_ELABORACAO' && c.status !== 'EM_ELABORACAO')) {
      justification = await askReason({ title: TRANSITION_BTN[target][0], text: target === 'CANCELADA' ? 'A campanha não poderá ser reativada.' : 'A aprovação jurídica será desfeita e precisará ser registrada de novo.', danger: target === 'CANCELADA', confirm: TRANSITION_BTN[target][0] });
      if (!justification) return;
    } else if (target === 'ENCERRADA' && !confirm('Encerrar as participações? O balcão deixa de aceitar comprovantes desta campanha.')) return;
    else if (target === 'ATIVA' && !confirm('Ativar a campanha? O balcão e os boxes passam a operar com ela.')) return;
    await withLoading(b, async () => {
      try { await api(`/campaigns/${c.id}/transition`, { method: 'POST', body: { target_status: target, justification } }); toast(`Campanha: ${statusLabel(target)}.`); await App.loadCampaigns(); campaignDetail(root, c.id); }
      catch (err) { fail(err); }
    });
  });
}
function legalHtml(c) {
  const can = c.status === 'AGUARDANDO_APROVACAO';
  const ck = c.legal_checklist || {};
  return `<h2>Aprovação jurídica</h2><p class="muted">${can ? 'Marque somente os itens comprovados por documento. Com os seis itens marcados, a campanha fica aprovada.' : c.status === 'EM_ELABORACAO' ? 'Disponível depois de enviar a campanha para aprovação.' : 'Situação dos itens obrigatórios.'}</p>
    <form id="lf">${Object.entries(c.legal_labels).map(([k, l]) => `<label class="check" style="margin:8px 0"><input type="checkbox" data-k="${k}" ${ck[k] ? 'checked' : ''} ${can ? '' : 'disabled'}><span>${esc(l)}</span></label>`).join('')}
    ${c.legal_approval_justification ? `<p style="margin-top:10px"><b>Parecer registrado:</b> ${esc(c.legal_approval_justification)}</p>` : ''}
    ${can ? `<div class="field" style="margin-top:12px"><label for="lj">Parecer jurídico / documento de referência</label><input id="lj" placeholder="Ex.: Parecer PGM nº 45/2026" required></div><button class="btn btn-primary" id="lBtn">Registrar aprovação</button>` : ''}</form>`;
}
function bindLegal(root, c) {
  const f = $('#lf', root);
  if (!f || c.status !== 'AGUARDANDO_APROVACAO') return;
  f.onsubmit = async (e) => {
    e.preventDefault();
    const body = { legal_promoter_name: c.legal_promoter_name || '', legal_promoter_doc: c.legal_promoter_doc || '', justification: $('#lj').value.trim() };
    if (body.justification.length < 5) { toast('Informe o parecer ou documento de referência.', 'warn'); return; }
    $$('[data-k]', f).forEach((i) => { body[i.dataset.k] = i.checked; });
    await withLoading($('#lBtn'), async () => {
      try { const r = await api(`/campaigns/${c.id}/legal-approvals`, { method: 'POST', body }); toast(r.campaign_status === 'APROVADA' ? 'Campanha aprovada.' : 'Aprovação parcial registrada.'); await App.loadCampaigns(); campaignDetail($('#view'), c.id); }
      catch (err) { fail(err); }
    });
  };
}

/* ================================================================== PERMISSIONÁRIOS E BOXES */
const BOX_LEGEND = [['CONFIRMADO', 'Confirmado'], ['PENDENTE_CONFERENCIA', 'Aguardando conferência'], ['EM_REGULARIZACAO', 'Em regularização'], ['VAGO_CONFIRMADO', 'Vago'], ['SEM_USO', 'Sem uso'], ['SEM_REGISTRO', 'Sem registro']];
const FLAG_TXT = { DUP_BOX_SPREADSHEET: 'Box repetido na planilha', EMPTY_NAME: 'Sem nome', MARKED_VAGO: 'Marcado como vago', EMPTY_ACTIVITY: 'Sem atividade', BOX_OUT_OF_MAP: 'Fora do mapa (1–368)' };
Pages.permissionarios = async (root, rest) => {
  root.innerHTML = `${pageHead('Permissionários e boxes', 'Mapa dos 368 boxes, cadastro dos permissionários e conferência da planilha oficial.')}
    ${tabsHtml([['mapa', 'Mapa dos boxes'], ['lista', 'Permissionários'], ['conf', 'Conferência da planilha']], rest[0] || 'mapa')}<div id="pb"></div>`;
  const body = $('#pb');
  const show = (t) => ({ mapa: boxMapTab, lista: permListTab, conf: stagingTab })[t](body);
  bindTabs(root, show);
  await show(rest[0] || 'mapa');
};
async function boxMapTab(body) {
  body.innerHTML = loadingBlock(6);
  const map = await api('/boxes/map');
  const counts = {}; map.forEach((b) => { counts[b.status] = (counts[b.status] || 0) + 1; });
  body.innerHTML = `${howto('Como ler o mapa', ['Cada quadrado é um box, numerado de 1 a 368.', 'A cor indica a situação oficial. Amarelo significa que a linha da planilha ainda precisa ser conferida.', 'Um traço vermelho embaixo indica divergência na planilha (box repetido, sem nome etc.).', 'Clique em um box para ver o titular e o histórico, <b>vincular ou trocar o titular</b>, encerrar o vínculo ou mudar a situação. Só boxes <b>confirmados</b> recebem talões.'])}
    <section class="panel"><div class="filters"><div class="field"><label for="mq">Localizar</label><input id="mq" placeholder="Número do box, nome ou atividade"></div>
      <div class="field"><label for="ms">Situação</label><select id="ms"><option value="">Todas</option>${BOX_LEGEND.map(([k, l]) => `<option value="${k}">${l} (${counts[k] || 0})</option>`).join('')}</select></div></div>
      <div class="legend" style="margin:0 0 14px">${BOX_LEGEND.map(([k, l]) => `<span><i class="bx-${k}" style="border:1px solid #c4cfd5"></i>${l} <b class="num">${counts[k] || 0}</b></span>`).join('')}</div>
      <div class="boxmap" id="bm">${map.map((b, i) => `<button class="bx-${b.status} ${b.flags.length ? 'flag' : ''}" data-i="${i}" title="Box ${b.box_number}${b.permissionario ? ' — ' + esc(b.permissionario) : ''}">${b.box_number}</button>`).join('')}</div></section>`;
  const filter = () => {
    const q = $('#mq').value.trim().toLowerCase(), s = $('#ms').value;
    $$('#bm button').forEach((btn) => {
      const b = map[+btn.dataset.i];
      const hit = (!s || b.status === s) && (!q || b.box_number === q || (b.permissionario || '').toLowerCase().includes(q) || (b.activity || '').toLowerCase().includes(q));
      btn.classList.toggle('dim', !hit);
    });
  };
  $('#mq').addEventListener('input', debounce(filter, 200)); $('#ms').onchange = filter;
  $$('#bm button').forEach((btn) => btn.onclick = () => boxDrawer(map[+btn.dataset.i].box_number, () => boxMapTab(body)));
}
async function permListTab(body) {
  body.innerHTML = `<div class="filters"><div class="field"><label for="pq">Buscar</label><input id="pq" placeholder="Nome ou número do box"></div>
    <div class="field"><label for="pst">Situação</label><select id="pst"><option value="">Todas</option>${['ATIVO', 'SUSPENSO', 'INATIVO', 'BLOQUEADO'].map((s) => `<option value="${s}">${statusLabel(s)}</option>`).join('')}</select></div>
    <button class="btn btn-secondary" id="pexp">${icon('baixar')}Exportar Excel</button>
    <button class="btn btn-primary" id="pnew">${icon('mais')}Novo permissionário</button></div><div id="pl">${loadingBlock(5)}</div>`;
  const load = async () => {
    const qs = new URLSearchParams(); if ($('#pq').value.trim()) qs.set('q', $('#pq').value.trim()); if ($('#pst').value) qs.set('status', $('#pst').value);
    try {
      const rows = await api(`/permissionarios?${qs}`);
      $('#pl').innerHTML = rows.length ? `<div class="table-wrap"><table><thead><tr><th>Permissionário</th><th>Boxes</th><th>Atividade</th><th>Situação</th><th>Portal</th></tr></thead><tbody>
        ${rows.map((p) => `<tr class="clickable" data-id="${p.id}" tabindex="0"><td><b>${esc(p.name)}</b></td><td class="num">${esc(p.boxes.join(', ') || '—')}</td><td>${esc(p.activities.join(', ') || '—')}</td><td>${chip(p.status)}</td><td>${p.has_portal_user ? '<span class="chip agua">Com acesso</span>' : '<small>Sem acesso</small>'}</td></tr>`).join('')}</tbody></table></div>`
        : emptyState('Nenhum permissionário encontrado.', 'Cadastre um novo permissionário ou aprove linhas na conferência da planilha.');
      $$('tr[data-id]', body).forEach((tr) => { tr.onclick = () => permDrawer(tr.dataset.id, load); tr.onkeydown = (e) => e.key === 'Enter' && permDrawer(tr.dataset.id, load); });
    } catch (e) { $('#pl').innerHTML = errorBlock(e); }
  };
  $('#pq').addEventListener('input', debounce(load, 300)); $('#pst').onchange = load;
  $('#pnew').onclick = () => newPermDrawer({ onDone: load });
  $('#pexp').onclick = () => downloadFile(`/reports/export/permissionarios.xlsx${S.campaignId ? `?campaign_id=${S.campaignId}` : ''}`, 'permissionarios.xlsx').catch(fail);
  await load();
}
async function permDrawer(id, reload) {
  const body = openDrawer('Permissionário', loadingBlock(6));
  try {
    const p = await api(`/permissionarios/${id}`);
    $('.drawer-head h2').textContent = p.name;
    body.innerHTML = `<dl class="kv"><dt>Situação</dt><dd>${chip(p.status)}</dd><dt>CPF/CNPJ</dt><dd>${esc(p.document || '—')}</dd><dt>Telefone</dt><dd>${esc(p.phone || '—')}</dd><dt>E-mail</dt><dd>${esc(p.email || '—')}</dd>
      <dt>Acesso ao portal</dt><dd>${p.portal_user ? esc(p.portal_user) : 'Não possui — crie em Usuários'}</dd><dt>Participações originadas</dt><dd>${fmtN(p.participations)}</dd></dl>
      <hr class="divider"><h3>Atualizar cadastro</h3>
      <form id="pe" style="margin-top:10px"><div class="row"><div class="field"><label for="peSt">Situação</label><select id="peSt">${['ATIVO', 'SUSPENSO', 'INATIVO', 'BLOQUEADO'].map((s) => `<option value="${s}" ${p.status === s ? 'selected' : ''}>${statusLabel(s)}</option>`).join('')}</select></div>
      <div class="field"><label for="peDoc">CPF/CNPJ</label><input id="peDoc" value="${esc(p.document || '')}"></div></div>
      <div class="row"><div class="field"><label for="pePh">Telefone</label><input id="pePh" value="${esc(p.phone || '')}"></div><div class="field"><label for="peEm">E-mail</label><input id="peEm" type="email" value="${esc(p.email || '')}"></div></div>
      <div class="field"><label for="peJ">Justificativa</label><input id="peJ" required placeholder="Ex.: Regularização conferida in loco"></div>
      <div class="hint" style="margin:-6px 0 12px">Permissionários fora da situação Ativo não recebem talões e seus comprovantes são recusados no balcão.</div>
      <button class="btn btn-primary">Salvar alterações</button></form>
      <hr class="divider"><div class="panel-head" style="margin-bottom:6px"><h3>Vínculos com boxes</h3><button class="btn btn-secondary btn-sm" id="peBox">${icon('box')}Vincular a um box</button></div>${p.occupancies.length ? `<ul class="timeline">${p.occupancies.map((o) => `<li><b><a href="javascript:void 0" data-boxlink="${esc(o.box_number)}">Box ${esc(o.box_number)}</a></b> — ${esc(o.activity)} ${o.is_current ? chip('ATIVO', 'Vigente') : ''}<small>${fmtDate(o.start_date)}${o.end_date ? ' a ' + fmtDate(o.end_date) : ''} · ${esc(o.term || '')}</small></li>`).join('')}</ul>` : emptyState('Sem vínculos.')}
      <hr class="divider"><h3>Talões recebidos</h3>${p.batches.length ? `<table><tbody>${p.batches.map((b) => `<tr><td><b>Lote #${b.batch_number}</b><span class="sub">${esc(b.campaign_name)}</span></td><td class="num">${esc(b.first_code)}–${esc(b.last_code.split('-')[1])}</td><td class="r num">${b.used}/${b.total}</td></tr>`).join('')}</tbody></table>` : emptyState('Nenhum talão.')}
      <hr class="divider"><h3>Histórico de alterações</h3>${p.history.length ? `<ul class="timeline">${p.history.map((h) => { const a = JSON.parse(h.after || '{}'); return `<li><b>${esc(a.status ? 'Situação: ' + statusLabel(a.status) : 'Cadastro atualizado')}</b><small>${fmtDateTime(h.timestamp)} · ${esc(h.username)} · ${esc(a.justification || '')}</small></li>`; }).join('')}</ul>` : emptyState('Sem alterações registradas.')}`;
    $('#peBox', body).onclick = () => assignDrawer({ permissionarioId: p.id, permissionarioName: p.name, onDone: () => { permDrawer(id, reload); if (reload) reload(); } });
    $$('[data-boxlink]', body).forEach((a) => a.onclick = () => boxDrawer(a.dataset.boxlink, reload));
    $('#pe', body).onsubmit = async (e) => {
      e.preventDefault();
      if ($('#peJ').value.trim().length < 5) { $('#peJ').classList.add('invalid'); toast('Informe a justificativa.', 'warn'); return; }
      try {
        await api(`/permissionarios/${id}`, { method: 'PATCH', body: { status: $('#peSt').value, document_cpf_cnpj: $('#peDoc').value.trim() || null, phone: $('#pePh').value.trim() || null, email: $('#peEm').value.trim() || null, justification: $('#peJ').value.trim() } });
        toast('Cadastro atualizado.'); permDrawer(id, reload); if (reload) reload();
      } catch (err) { fail(err); }
    };
  } catch (e) { body.innerHTML = errorBlock(e); }
}
async function stagingTab(body) {
  body.innerHTML = `${howto('Como conferir a planilha', ['A planilha oficial é carregada uma única vez; cada linha precisa de uma decisão do gestor.', 'Linhas com divergência aparecem marcadas (box repetido, sem nome, vago).', '<b>Aprovar</b> cria ou atualiza o box e o vínculo com o permissionário. Use <b>Corrigir e aprovar</b> quando os dados precisarem de ajuste.', '<b>Rejeitar</b> descarta a linha mantendo o registro da decisão.', 'Toda decisão exige justificativa e fica na auditoria.'])}
    <div class="filters"><div class="field"><label for="sq">Buscar</label><input id="sq" placeholder="Box ou nome"></div>
    <div class="field"><label for="sst">Situação</label><select id="sst"><option value="PENDENTE_REVISAO">Pendentes</option><option value="">Todas</option><option value="APROVADO">Aprovadas</option><option value="REJEITADO">Rejeitadas</option></select></div>
    <label class="check" style="margin-bottom:10px"><input type="checkbox" id="sfl"><span>Só com divergência</span></label>
    <button class="btn btn-secondary" id="sbulk" disabled>Aprovar selecionadas</button></div><div id="sl">${loadingBlock(6)}</div>`;
  let rows = [];
  let offset = 0;
  const PAGE = 50;
  const load = async () => {
    const qs = new URLSearchParams({ limit: PAGE, offset }); if ($('#sst').value) qs.set('status_filter', $('#sst').value); if ($('#sfl').checked) qs.set('only_flagged', 'true'); if ($('#sq').value.trim()) qs.set('q', $('#sq').value.trim());
    try {
      const r = await api(`/boxes/staging?${qs}`);
      rows = r.rows;
      if (!r.total && !r.pending_total && !$('#sq').value && $('#sst').value === 'PENDENTE_REVISAO') {
        const all = await api('/boxes/staging?limit=1');
        if (!all.total) { $('#sl').innerHTML = emptyState('A planilha ainda não foi carregada.', 'Carregue a planilha oficial de permissionários (pasta data/) para iniciar a conferência.', `<button class="btn btn-primary" id="simp">Carregar planilha oficial</button>`); $('#simp').onclick = async () => { try { const x = await api('/boxes/import-staging', { method: 'POST' }); toast(`${x.total_rows_imported} linhas carregadas, ${x.anomalies_detected} com divergência.`); load(); } catch (e) { fail(e); } }; return; }
      }
      $('#sl').innerHTML = `<p class="muted">${fmtN(r.total)} linha(s) nesta visão · ${fmtN(r.pending_total)} pendente(s) no total.</p>` + (rows.length ? `<div class="table-wrap"><table><thead><tr><th><input type="checkbox" id="sall" aria-label="Selecionar todas"></th><th>Linha</th><th>Box</th><th>Nome na planilha</th><th>Atividade</th><th>Divergências</th><th>Situação</th><th></th></tr></thead><tbody>
        ${rows.map((x) => { const flags = JSON.parse(x.discrepancy_flags || '[]'); const pend = x.status === 'PENDENTE_REVISAO'; return `<tr><td>${pend && !flags.length ? `<input type="checkbox" data-sel="${x.id}" aria-label="Selecionar linha ${x.row_number}">` : ''}</td><td class="num">${x.row_number}</td><td class="num"><b>${esc(x.box_number || '—')}</b></td><td>${esc(x.permissionario_name || '—')}</td><td>${esc(x.activity || '—')}</td>
          <td>${flags.map((f) => `<span class="chip bad">${esc(FLAG_TXT[f] || f)}</span>`).join(' ') || '<small>—</small>'}</td><td>${chip(x.status)}${x.admin_justification ? `<span class="sub">${esc(x.admin_justification)}</span>` : ''}</td>
          <td class="r">${pend ? `<button class="btn btn-ghost btn-sm" data-rev="${x.id}">Revisar</button>` : ''}</td></tr>`; }).join('')}</tbody></table></div>
        <div class="pager"><span>${offset + 1}–${offset + rows.length} de ${fmtN(r.total)}</span><button class="btn btn-secondary btn-sm" id="sPrev" ${offset ? '' : 'disabled'}>Anteriores</button><button class="btn btn-secondary btn-sm" id="sNext" ${offset + PAGE < r.total ? '' : 'disabled'}>Próximas</button></div>` : emptyState('Nenhuma linha nesta visão.'));
      if ($('#sPrev')) { $('#sPrev').onclick = () => { offset = Math.max(0, offset - PAGE); load(); }; $('#sNext').onclick = () => { offset += PAGE; load(); }; }
      $$('[data-rev]').forEach((b) => b.onclick = () => reviewDrawer(rows.find((x) => String(x.id) === b.dataset.rev), load));
      const updBulk = () => { const n = $$('[data-sel]:checked').length; $('#sbulk').disabled = !n; $('#sbulk').textContent = n ? `Aprovar ${n} selecionada(s)` : 'Aprovar selecionadas'; };
      $$('[data-sel]').forEach((c) => c.onchange = updBulk);
      if ($('#sall')) $('#sall').onchange = (e) => { $$('[data-sel]').forEach((c) => { c.checked = e.target.checked; }); updBulk(); };
      updBulk();
    } catch (e) { $('#sl').innerHTML = errorBlock(e); }
  };
  const reset = () => { offset = 0; load(); };
  $('#sq').addEventListener('input', debounce(reset, 300)); $('#sst').onchange = reset; $('#sfl').onchange = reset;
  $('#sbulk').onclick = async () => {
    const ids = $$('[data-sel]:checked').map((c) => +c.dataset.sel);
    const j = await askReason({ title: `Aprovar ${ids.length} linha(s)`, text: 'Somente linhas sem divergência podem ser aprovadas em lote, sem correções.', confirm: 'Aprovar', min: 5 });
    if (!j) return;
    try { const r = await api('/boxes/staging/review', { method: 'POST', body: { staging_row_ids: ids, decision: 'APROVADO', justification: j } }); toast(`${r.reviewed_count} linha(s) aprovada(s).`); load(); } catch (e) { fail(e); }
  };
  await load();
}
function reviewDrawer(x, reload) {
  const flags = JSON.parse(x.discrepancy_flags || '[]');
  const body = openDrawer(`Linha ${x.row_number} da planilha`, `${flags.length ? notice('warn', 'Divergências encontradas', flags.map((f) => esc(FLAG_TXT[f] || f)).join(', ') + '.') : ''}
    <form id="rv"><div class="row"><div class="field"><label for="rvBox">Box</label><input id="rvBox" value="${esc(x.box_number || '')}" inputmode="numeric"></div><div class="field"><label for="rvAct">Atividade</label><input id="rvAct" value="${esc(x.activity || '')}"></div></div>
    <div class="field"><label for="rvName">Permissionário</label><input id="rvName" value="${esc((x.permissionario_name || '').replace(/\.$/, ''))}"></div>
    <label class="check" style="margin-bottom:14px"><input type="checkbox" id="rvVago" ${flags.includes('MARKED_VAGO') ? 'checked' : ''}><span>Box vago (não vincular permissionário)</span></label>
    <div class="field"><label for="rvJ">Justificativa</label><textarea id="rvJ" placeholder="Ex.: Conferido in loco em 03/11 com o fiscal do complexo."></textarea></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" data-d="APROVADO">Aprovar</button><button type="button" class="btn btn-danger" data-d="REJEITADO">Rejeitar</button></div></form>`);
  $$('[data-d]', body).forEach((b) => b.onclick = async (e) => {
    e.preventDefault();
    const j = $('#rvJ').value.trim();
    if (j.length < 5) { $('#rvJ').classList.add('invalid'); toast('Informe a justificativa (mínimo 5 caracteres).', 'warn'); return; }
    const changed = $('#rvBox').value.trim() !== (x.box_number || '') || $('#rvName').value.trim() !== (x.permissionario_name || '').replace(/\.$/, '') || $('#rvAct').value.trim() !== (x.activity || '');
    const payload = { staging_row_ids: [x.id], decision: b.dataset.d, justification: j, is_vago: $('#rvVago').checked };
    if (changed) Object.assign(payload, { confirmed_box_number: $('#rvBox').value.trim(), confirmed_permissionario_name: $('#rvName').value.trim(), confirmed_activity: $('#rvAct').value.trim() });
    await withLoading(b, async () => {
      try { await api('/boxes/staging/review', { method: 'POST', body: payload }); toast(b.dataset.d === 'APROVADO' ? `Box ${$('#rvBox').value} confirmado.` : 'Linha rejeitada.'); closeOverlay(); reload(); } catch (err) { fail(err); }
    });
  });
}

/* ================================================================== PORTAL DO PERMISSIONÁRIO */
Pages.portal = async (root, rest) => {
  const isAdmin = S.user.role === 'ADMIN';
  let permId = rest[0] || null;
  let perms = [];
  if (isAdmin) perms = (await api('/permissionarios')).filter((p) => p.boxes.length);
  const d = await api(`/portal/overview${permId ? `?permissionario_id=${permId}` : ''}`);
  permId = d.permissionario.id;
  const t = d.totals;
  const boxes = d.linked_boxes.map((b) => b.box_number).join(', ');
  const camp = d.active_campaigns[0];
  const irregular = d.permissionario.status !== 'ATIVO';
  root.innerHTML = `${isAdmin ? `<div class="filters"><div class="field" style="min-width:320px"><label for="asPerm">Visualizar o portal como</label><select id="asPerm">${perms.map((p) => `<option value="${p.id}" ${p.id === permId ? 'selected' : ''}>Box ${esc(p.boxes.join(', '))} — ${esc(p.name)}</option>`).join('')}</select></div><small style="margin-bottom:10px">Você vê exatamente o que o permissionário vê.</small></div>` : ''}
    ${pageHead(`Olá, ${d.permissionario.name.split(' ')[0]}`, `Box ${esc(boxes || '—')} · ${esc(d.linked_boxes.map((b) => b.activity).join(', '))} · Cadastro ${chip(d.permissionario.status)}`)}
    ${irregular ? notice('bad', 'Seu cadastro não está ativo', 'Enquanto o cadastro estiver irregular, você não pode emitir comprovantes e o balcão recusa os comprovantes do seu box. Procure a administração do complexo.') : ''}
    ${camp ? notice('info', `Campanha ativa: ${camp.name}`, `Compras até <b>${fmtDate(camp.purchase_end_date)}</b>. Valor mínimo por comprovante: <b>${fmtMoney(camp.min_purchase_value)}</b>. O consumidor deve levar o comprovante ao balcão até <b>${fmtDate(camp.registration_end_date)}</b>.`) : notice('warn', 'Nenhuma campanha ativa no momento', '')}
    <div class="stats">
      <div class="stat"><div class="v">${fmtN(t.available)}</div><div class="l">Disponíveis</div><div class="s">ainda com você</div></div>
      <div class="stat"><div class="v">${fmtN(t.issued)}</div><div class="l">Entregues a clientes</div><div class="s">aguardando o balcão</div></div>
      <div class="stat"><div class="v">${fmtN(t.used)}</div><div class="l">Utilizados</div><div class="s">viraram número da sorte</div></div>
      <div class="stat"><div class="v">${fmtN(t.incidents)}</div><div class="l">Ocorrências</div><div class="s">extraviados, devolvidos, cancelados</div></div>
    </div>
    <div class="grid g2">
      <section class="panel"><div class="panel-head"><div><h2>Entregar comprovante ao cliente</h2><p>Registre a venda ao entregar o comprovante. Isso ajuda a comprovar a compra no balcão.</p></div></div>
        <form id="iss"><div class="field"><label for="issCode">Código do comprovante</label><input id="issCode" placeholder="Ex.: NATAL-00005" required ${irregular ? 'disabled' : ''}></div>
        <div class="row"><div class="field"><label for="issVal">Valor da compra (R$)</label><input id="issVal" type="number" step="0.01" min="0.01" required ${irregular ? 'disabled' : ''}></div>
        <div class="field"><label for="issDoc">Nota ou cupom fiscal <small>(opcional)</small></label><input id="issDoc" ${irregular ? 'disabled' : ''}></div></div>
        <button class="btn btn-primary" id="issBtn" ${irregular ? 'disabled' : ''}>Registrar entrega</button></form><div id="issOut"></div></section>
      <section class="panel"><div class="panel-head"><div><h2>Comunicar problema com comprovante</h2><p>Use quando um comprovante for perdido, danificado ou devolvido sem uso.</p></div></div>
        <form id="inc"><div class="field"><label for="incCode">Código do comprovante</label><input id="incCode" required ${irregular ? 'disabled' : ''}></div>
        <div class="field"><label for="incSt">O que aconteceu</label><select id="incSt" ${irregular ? 'disabled' : ''}><option value="EXTRAVIADO">Foi perdido (extraviado)</option><option value="DEVOLVIDO">Foi devolvido sem uso</option><option value="CANCELADO">Foi danificado / quero cancelar</option></select></div>
        <div class="field"><label for="incR">Explique brevemente</label><input id="incR" required ${irregular ? 'disabled' : ''}></div>
        <button class="btn btn-secondary" id="incBtn" ${irregular ? 'disabled' : ''}>Registrar ocorrência</button></form></section>
    </div>
    <section class="panel" style="margin-top:16px"><div class="panel-head"><h2>Meus talões</h2></div>
      ${d.batches.length ? `<div class="table-wrap"><table><thead><tr><th>Lote</th><th>Campanha</th><th>Numeração</th><th>Uso</th><th class="r">Disponíveis</th></tr></thead><tbody>${d.batches.map((b) => `<tr><td><b>#${b.batch_number}</b></td><td>${esc(b.campaign_name)}</td><td class="num">${esc(b.first_code)} a ${esc(b.last_code)}</td><td><div class="progress"><b style="width:${(100 * b.used) / b.total}%"></b></div><span class="sub">${b.used} de ${b.total} utilizados</span></td><td class="r num">${fmtN(b.available)}</td></tr>`).join('')}</tbody></table></div>` : emptyState('Você ainda não recebeu talões.', 'A administração distribui os talões aos boxes confirmados.')}
    </section>
    <div class="grid g2" style="margin-top:16px">
      <section class="panel"><div class="panel-head"><div><h2>Números da sorte gerados no seu box</h2><p>${fmtN(t.participations)} no total</p></div></div>
        ${d.recent_participations.length ? `<table><tbody>${d.recent_participations.slice(0, 12).map((p) => `<tr><td class="num"><b>${esc(p.lucky_number)}</b></td><td class="num">${esc(p.voucher_code)}</td><td class="r"><small>${fmtDateTime(p.validated_at)}</small></td></tr>`).join('')}</tbody></table>` : emptyState('Nenhum comprovante do seu box foi validado ainda.')}</section>
      <section class="panel"><h2 style="margin-bottom:10px">Orientações</h2><ol class="steps">
        <li><b>Entregue um comprovante por compra</b><small>Só para compras a partir do valor mínimo da campanha.</small></li>
        <li><b>Registre a entrega aqui</b><small>Informe o código, o valor e, se houver, a nota fiscal.</small></li>
        <li><b>Oriente o cliente</b><small>Ele leva o comprovante ao balcão central com CPF para receber o número da sorte.</small></li>
        <li><b>Comunique problemas no mesmo dia</b><small>Comprovante perdido ou danificado deve ser registrado para não ser usado indevidamente.</small></li></ol></section>
    </div>`;
  if (isAdmin) $('#asPerm').onchange = (e) => { location.hash = `#/portal/${e.target.value}`; };
  $('#iss').onsubmit = async (e) => {
    e.preventDefault();
    await withLoading($('#issBtn'), async () => {
      try {
        const r = await api('/portal/issue-voucher', { method: 'POST', body: { voucher_code: $('#issCode').value.trim(), issued_value: +$('#issVal').value, invoice_doc_number: $('#issDoc').value.trim() || null } });
        $('#issOut').innerHTML = `<div class="qr-box"><img id="issQr" alt="QR Code do comprovante ${esc(r.voucher_code)}"><div><b>${esc(r.voucher_code)} entregue</b><p class="muted" style="margin:4px 0 0">${fmtMoney(r.issued_value)} · ${fmtDateTime(r.issued_at)}. O cliente pode apresentar este QR Code ou o comprovante impresso no balcão.</p></div></div>`;
        const res = await api(`/vouchers/${encodeURIComponent(r.voucher_code)}/qr.svg`, { raw: true });
        $('#issQr').src = URL.createObjectURL(await res.blob());
        toast(r.message); $('#iss').reset();
      } catch (err) { fail(err); }
    });
  };
  $('#inc').onsubmit = async (e) => {
    e.preventDefault();
    if ($('#incR').value.trim().length < 5) { toast('Explique o que aconteceu (mínimo 5 caracteres).', 'warn'); return; }
    await withLoading($('#incBtn'), async () => {
      try { const r = await api('/portal/report-incident', { method: 'POST', body: { voucher_code: $('#incCode').value.trim(), status: $('#incSt').value, reason: $('#incR').value.trim() } }); toast(r.message); Pages.portal(root, isAdmin ? [permId] : []); }
      catch (err) { fail(err); }
    });
  };
};

/* ================================================================== APURAÇÃO */
Pages.apuracao = async (root) => {
  const camp = currentCampaign();
  if (!camp) { root.innerHTML = pageHead('Apuração', '') + emptyState('Nenhuma campanha selecionada.'); return; }
  const ov = await api(`/draw/overview/${camp.id}`);
  const integ = ov.integrity;
  const closed = ov.campaign.status === 'ENCERRADA';
  const frozen = integ.frozen;
  const pendingPrizes = ov.prizes.filter((p) => !p.drawn);
  const stepState = [closed, frozen, ov.prizes.length > 0 && !pendingPrizes.length, ov.results.some((r) => r.status === 'VALIDO' && r.delivery_status === 'ENTREGUE')];
  const cur = stepState.indexOf(false);
  const conc = ov.concentration;
  root.innerHTML = `${pageHead('Apuração', `Campanha <b>${esc(ov.campaign.name)}</b> ${chip(ov.campaign.status)}`, `<button class="btn btn-secondary" id="btnBase">${icon('baixar')}Base (CSV)</button><button class="btn btn-secondary" id="btnAta">${icon('imprimir')}Emitir ata</button>`)}
    <section class="panel" style="margin-bottom:16px"><ol class="steps horizontal">
      ${['Encerrar participações', 'Congelar a base', 'Registrar a extração', 'Entregar o prêmio'].map((t, i) => `<li class="${stepState[i] ? 'done' : i === cur ? 'current' : ''}"><b>${t}</b></li>`).join('')}</ol></section>
    ${conc && conc.is_concentrated ? notice('warn', 'Atenção: a regra atual concentra a chance de ganhar', `Com ${fmtN(conc.participants)} números emitidos em sequência e a regra configurada, o número <b>${esc(conc.top_number)}</b> vence em <b>${conc.top_share_pct.toLocaleString('pt-BR')}%</b> dos resultados possíveis da Loteria Federal — numa distribuição equânime, cada número teria ${conc.fair_share_pct.toLocaleString('pt-BR')}%. Valide a forma de distribuição dos números e a regra de aproximação com o jurídico antes da apuração oficial (ver DIAGNOSTICO.md, item A1).`) : ''}
    ${conc && conc.no_winner_pct > 50 ? notice('info', 'Regra "somente número exato"', `Em ${conc.no_winner_pct.toLocaleString('pt-BR')}% das extrações possíveis não haverá número idêntico e o prêmio não será atribuído nesta extração.`) : ''}
    <div class="grid g-side">
      <div>
        <section class="panel"><div class="panel-head"><h2>Base de participações</h2>${frozen ? (integ.intact ? chip('VALIDO', 'Íntegra') : chip('ANULADO', 'Divergente')) : chip('PENDENTE', 'Não congelada')}</div>
          <dl class="kv"><dt>Participações elegíveis</dt><dd class="num">${fmtN(ov.eligible_count)}</dd><dt>Consumidores únicos</dt><dd class="num">${fmtN(ov.unique_participants)}</dd>
          ${frozen ? `<dt>Números</dt><dd class="num">${esc(integ.snapshot.first_lucky_number)} a ${esc(integ.snapshot.last_lucky_number)}</dd><dt>Congelada em</dt><dd>${fmtDateTime(integ.snapshot.frozen_at)} por ${esc(integ.snapshot.frozen_by)}</dd><dt>SHA-256 congelado</dt><dd class="mono">${esc(integ.snapshot.sha256)}</dd>` : ''}
          <dt>SHA-256 atual</dt><dd class="mono">${esc(integ.current_sha256)}</dd><dt>Regra de aproximação</dt><dd>${esc(ov.campaign.rule_text || 'Não definida na campanha')}</dd></dl>
          <p class="muted" style="font-size:13px;margin-top:12px">O hash é calculado sobre o arquivo "Base (CSV)". Qualquer pessoa pode baixá-lo e conferir com <span class="mono">sha256sum</span>.</p>
          <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
            ${ov.campaign.status === 'ATIVA' ? `<button class="btn btn-primary" id="btnClose">Encerrar participações</button>` : ''}
            ${closed && !frozen ? `<button class="btn btn-primary" id="btnFreeze" ${ov.eligible_count ? '' : 'disabled'}>${icon('cadeado')}Congelar base</button>` : ''}
          </div></section>
        <section class="panel"><div class="panel-head"><h2>Registrar extração da Loteria Federal</h2></div>
          ${!frozen ? notice('info', 'Disponível após congelar a base', 'Encerre as participações e congele a base para registrar a extração.') : !pendingPrizes.length && ov.prizes.length ? notice('ok', 'Todos os prêmios foram apurados', 'Para refazer um resultado, anule-o com justificativa formal.') : `
          <form id="dr"><div class="row"><div class="field"><label for="drPrize">Prêmio</label><select id="drPrize">${pendingPrizes.map((p) => `<option value="${p.id}">${p.position}º — ${esc(p.title)}</option>`).join('')}</select></div>
          <div class="field"><label for="drContest">Concurso</label><input id="drContest" inputmode="numeric" required placeholder="Ex.: 5912"></div>
          <div class="field"><label for="drDate">Data da extração</label><input id="drDate" type="date" required></div></div>
          <label>Prêmios da extração (1º ao 5º)</label><div class="digits">${[1, 2, 3, 4, 5].map((i) => `<div class="field"><input data-p="${i}" inputmode="numeric" maxlength="6" placeholder="${i}º" aria-label="${i}º prêmio"></div>`).join('')}</div>
          <p class="hint" style="margin:8px 0 4px">Digite os 5 algarismos de cada bilhete, como publicados pela Caixa (ex.: 07.815). O número apurado é formado pela unidade de cada prêmio:</p>
          <div class="target" id="drTarget">${'<span class="empty-d">–</span>'.repeat(5)}</div>
          <button class="btn btn-primary" id="drBtn" style="margin-top:16px">${icon('apuracao')}Registrar e apurar</button></form>`}
        </section>
      </div>
      <section class="panel"><div class="panel-head"><h2>Resultados</h2></div><div id="res">${resultsHtml(ov.results)}</div></section>
    </div>`;
  const reload = () => Pages.apuracao(root);
  $('#btnBase').onclick = () => downloadFile(`/draw/base/${camp.id}.csv`, 'base.csv').catch(fail);
  $('#btnAta').onclick = () => openHtml(`/draw/minutes/${camp.id}`).catch(fail);
  if ($('#btnClose')) $('#btnClose').onclick = async () => {
    if (!confirm('Encerrar participações? O balcão deixa de aceitar comprovantes desta campanha.')) return;
    try { await api(`/campaigns/${camp.id}/transition`, { method: 'POST', body: { target_status: 'ENCERRADA' } }); toast('Participações encerradas.'); await App.loadCampaigns(); reload(); } catch (e) { fail(e); }
  };
  if ($('#btnFreeze')) $('#btnFreeze').onclick = async () => {
    if (!confirm(`Congelar a base com ${ov.eligible_count} participações? Depois disso, o hash fica registrado e não pode ser refeito.`)) return;
    try { const r = await api('/draw/freeze', { method: 'POST', body: { campaign_id: camp.id } }); toast(`Base congelada: ${r.participations_count} participações.`); reload(); } catch (e) { fail(e); }
  };
  if ($('#dr')) {
    const upd = () => {
      $('#drTarget').innerHTML = $$('[data-p]').map((i) => { const d = i.value.replace(/\D/g, ''); return d.length === 5 ? `<span>${d[4]}</span>` : '<span class="empty-d">–</span>'; }).join('');
    };
    $$('[data-p]').forEach((i) => i.addEventListener('input', () => { i.classList.toggle('invalid', i.value && i.value.replace(/\D/g, '').length !== 5); upd(); }));
    $('#dr').onsubmit = async (e) => {
      e.preventDefault();
      const prizes = $$('[data-p]').map((i) => i.value.trim());
      if (prizes.some((p) => p.replace(/\D/g, '').length !== 5)) { toast('Cada prêmio precisa ter 5 algarismos.', 'warn'); return; }
      if (!$('#drDate').value) { toast('Informe a data da extração.', 'warn'); return; }
      const target = prizes.map((p) => p.replace(/\D/g, '')[4]).join('');
      if (!confirm(`Confirmar a apuração do concurso ${$('#drContest').value} com número apurado ${target}? O resultado fica registrado e só pode ser anulado com justificativa formal.`)) return;
      await withLoading($('#drBtn'), async () => {
        try {
          const r = await api('/draw/execute-federal', { method: 'POST', body: { campaign_id: camp.id, prize_id: +$('#drPrize').value, contest_number: $('#drContest').value.trim(), draw_date: `${$('#drDate').value}T22:00:00`, extraction_prizes: prizes } });
          toast(r.winner_name ? `Número contemplado: ${r.winner_lucky_number}.` : 'Apuração registrada sem contemplado.');
          if (r.previous_wins_same_participant && r.previous_wins_same_participant.length) toast(`Atenção: este consumidor já foi contemplado em: ${r.previous_wins_same_participant.join(', ')}. Confira o regulamento.`, 'warn');
          reload();
        } catch (err) { fail(err); }
      });
    };
  }
  $$('[data-annul]').forEach((b) => b.onclick = async () => {
    const reason = await askReason({ title: 'Anular apuração', text: 'A anulação fica registrada na ata e na auditoria. Use somente com autorização formal (ex.: erro de digitação da extração reconhecido em ofício).', min: 20, confirm: 'Anular resultado', danger: true });
    if (!reason) return;
    try { await api(`/draw/${b.dataset.annul}/annul`, { method: 'POST', body: { reason } }); toast('Apuração anulada. O prêmio pode ser apurado novamente.'); reload(); } catch (e) { fail(e); }
  });
  $$('[data-deliv]').forEach((b) => b.onclick = () => {
    const body = openDrawer('Atualizar entrega do prêmio', `<form id="dv"><div class="field"><label for="dvSt">Situação</label><select id="dvSt">${['CONTATADO', 'ENTREGUE', 'NAO_LOCALIZADO', 'RECUSADO', 'PENDENTE'].map((s) => `<option value="${s}">${statusLabel(s)}</option>`).join('')}</select></div>
      <div class="field"><label for="dvN">Registro</label><textarea id="dvN" placeholder="Ex.: Contato por telefone em 05/11; entrega com termo assinado."></textarea></div><button class="btn btn-primary">Salvar</button></form>`, { modal: true });
    $('#dv', body).onsubmit = async (e) => {
      e.preventDefault();
      if ($('#dvSt').value === 'ENTREGUE' && !confirm('Registrar a entrega? Depois disso, a apuração não pode mais ser anulada pelo sistema.')) return;
      try { await api(`/draw/${b.dataset.deliv}/delivery`, { method: 'POST', body: { delivery_status: $('#dvSt').value, delivery_notes: $('#dvN').value.trim() || null } }); closeOverlay(); toast('Entrega atualizada.'); reload(); } catch (err) { fail(err); }
    };
  });
};
function resultsHtml(results) {
  if (!results.length) return emptyState('Nenhuma apuração registrada.', 'O resultado aparece aqui assim que a extração for registrada.');
  return results.slice().reverse().map((r) => `<article style="padding:14px 0;border-bottom:1px solid var(--line-2)${r.status === 'ANULADO' ? ';opacity:.6' : ''}">
    <div class="panel-head" style="margin-bottom:8px"><div><h3>${esc(r.prize_title)}</h3><p>Concurso ${esc(r.contest_number)} · ${fmtDate(r.draw_date)} · apurado por ${esc(r.executed_by || '—')}</p></div>${chip(r.status)}</div>
    <div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap"><div><small>Extração</small><div class="num">${r.extraction.map(esc).join(' · ')}</div></div>
      <div><small>Número apurado</small><div class="num"><b>${esc(r.target_number || '—')}</b></div></div>
      <div><small>Contemplado</small><div style="font-family:var(--font-display);font-size:26px;font-weight:800;color:var(--rio)">${esc(r.winner_lucky_number)}</div></div>
      <div><small>Correspondência</small><div>${r.match_type === 'EXATO' ? chip('VALIDO', 'Exata') : r.match_type === 'APROXIMADO' ? chip('PENDENTE', `Aproximada (${r.distance})`) : chip('SEM_CONTEMPLADO', 'Sem número idêntico')}</div></div></div>
    ${r.winner_name ? `<p style="margin:10px 0 4px"><b>${esc(r.winner_name)}</b> · ${esc(r.winner_cpf_masked)} · comprovante ${esc(r.voucher_code)} · box ${esc(r.box_number)}</p>` : ''}
    ${r.status === 'ANULADO' ? `<p class="muted" style="font-size:13px">Anulado por ${esc(r.annulled_by)} em ${fmtDateTime(r.annulled_at)}: ${esc(r.annulled_reason)}</p>` : `
      ${r.winner_name ? `<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:6px">Entrega: ${chip(r.delivery_status)}${r.delivery_status !== 'ENTREGUE' ? `<button class="btn btn-secondary btn-sm" data-deliv="${r.id}">Atualizar entrega</button>` : ''}${r.delivery_status !== 'ENTREGUE' ? `<button class="btn btn-ghost btn-sm" style="color:var(--bad)" data-annul="${r.id}">Anular</button>` : ''}</div>` : `<button class="btn btn-ghost btn-sm" style="color:var(--bad)" data-annul="${r.id}">Anular</button>`}
      ${r.delivery_events.length ? `<ul class="timeline" style="margin-top:8px">${r.delivery_events.map((e) => `<li><b>${esc(statusLabel(e.status))}</b>${e.notes ? ' — ' + esc(e.notes) : ''}<small>${fmtDateTime(e.created_at)} · ${esc(e.username)}</small></li>`).join('')}</ul>` : ''}`}
  </article>`).join('');
}

/* ================================================================== AUDITORIA E RELATÓRIOS */
const REPORTS = [
  ['participacoes', 'Participações validadas', 'Números da sorte, comprovante, box e consumidor (CPF mascarado).'],
  ['lotes', 'Distribuição de talões', 'Prestação de contas por lote: emitidos, utilizados, disponíveis e ocorrências.'],
  ['permissionarios', 'Permissionários', 'Boxes, atividade, situação e uso de comprovantes.'],
  ['ocorrencias', 'Recusas no balcão', 'Tentativas recusadas com o motivo.'],
  ['auditoria', 'Histórico de auditoria', 'Aplica os filtros escolhidos acima.'],
];
Pages.auditoria = async (root) => {
  root.innerHTML = `${pageHead('Auditoria e relatórios', 'Tudo o que muda no sistema fica registrado com data, responsável e situação antes e depois.')}
    ${tabsHtml([['hist', 'Histórico'], ['rel', 'Relatórios']], 'hist')}<div id="ab"></div>`;
  const body = $('#ab');
  bindTabs(root, (t) => (t === 'hist' ? auditList(body, {}) : reportsTab(body)));
  await auditList(body, {});
};
let AUDIT_FILTERS = {};
async function auditList(body, fixed) {
  const embedded = !!fixed.campaign_id;
  const actions = (await api('/reports/audit-trail?paged=true&limit=1')).actions;
  body.innerHTML = `<div class="filters">
    <div class="field"><label for="auU">Usuário</label><input id="auU"></div>
    <div class="field"><label for="auA">Operação</label><select id="auA"><option value="">Todas</option>${Object.entries(actions).map(([k, l]) => `<option value="${k}">${esc(l)}</option>`).join('')}</select></div>
    ${embedded ? '' : `<div class="field"><label for="auC">Campanha</label><select id="auC">${campaignOptions('', { allLabel: 'Todas' })}</select></div>`}
    <div class="field"><label for="auF">De</label><input type="date" id="auF"></div><div class="field"><label for="auT">Até</label><input type="date" id="auT"></div>
    <div class="field"><label for="auQ">Contém</label><input id="auQ" placeholder="Código, número, nome…"></div>
    <button class="btn btn-secondary" id="auX">${icon('baixar')}Excel</button></div><div id="aul">${loadingBlock(6)}</div>`;
  let offset = 0;
  const filters = () => {
    const f = { username: $('#auU').value.trim(), action: $('#auA').value, campaign_id: fixed.campaign_id || ($('#auC') ? $('#auC').value : ''), date_from: $('#auF').value, date_to: $('#auT').value, q: $('#auQ').value.trim() };
    Object.keys(f).forEach((k) => !f[k] && delete f[k]); AUDIT_FILTERS = f; return f;
  };
  const load = async () => {
    const qs = new URLSearchParams({ ...filters(), paged: true, limit: 25, offset });
    try {
      const r = await api(`/reports/audit-trail?${qs}`);
      $('#aul').innerHTML = r.items.length ? `<div class="table-wrap"><table><thead><tr><th>Quando</th><th>Quem</th><th>Operação</th><th>Registro</th><th></th></tr></thead><tbody>
        ${r.items.map((l, i) => `<tr><td class="num">${fmtDateTime(l.timestamp)}</td><td>${esc(l.username)}</td><td>${esc(l.action_label)}</td><td><small>${esc(l.entity)} ${esc(l.entity_id || '')}</small></td><td class="r">${l.before || l.after ? `<button class="btn btn-ghost btn-sm" data-i="${i}">Ver</button>` : ''}</td></tr>`).join('')}</tbody></table></div>
        <div class="pager"><span>${offset + 1}–${offset + r.items.length} de ${fmtN(r.total)}</span><button class="btn btn-secondary btn-sm" id="auPrev" ${offset ? '' : 'disabled'}>Anteriores</button><button class="btn btn-secondary btn-sm" id="auNext" ${offset + 25 < r.total ? '' : 'disabled'}>Próximos</button></div>`
        : emptyState('Nenhum registro com esses filtros.');
      $$('[data-i]', body).forEach((b) => b.onclick = () => {
        const l = r.items[+b.dataset.i];
        const pretty = (j) => { try { return esc(JSON.stringify(JSON.parse(j), null, 2)); } catch (_) { return esc(j); } };
        openDrawer(l.action_label, `<dl class="kv"><dt>Quando</dt><dd>${fmtDateTime(l.timestamp)}</dd><dt>Quem</dt><dd>${esc(l.username)}</dd><dt>Registro</dt><dd>${esc(l.entity)} ${esc(l.entity_id || '')}</dd>${l.ip ? `<dt>IP</dt><dd>${esc(l.ip)}</dd>` : ''}</dl>
          ${l.before ? `<h3 style="margin-top:16px">Antes</h3><pre class="mono" style="background:var(--neutral-soft);padding:10px;border-radius:6px;white-space:pre-wrap">${pretty(l.before)}</pre>` : ''}
          ${l.after ? `<h3 style="margin-top:16px">Depois</h3><pre class="mono" style="background:var(--neutral-soft);padding:10px;border-radius:6px;white-space:pre-wrap">${pretty(l.after)}</pre>` : ''}`);
      });
      if ($('#auPrev')) { $('#auPrev').onclick = () => { offset = Math.max(0, offset - 25); load(); }; $('#auNext').onclick = () => { offset += 25; load(); }; }
    } catch (e) { $('#aul').innerHTML = errorBlock(e); }
  };
  const reset = () => { offset = 0; load(); };
  ['auU', 'auQ'].forEach((id) => $('#' + id).addEventListener('input', debounce(reset, 350)));
  ['auA', 'auC', 'auF', 'auT'].forEach((id) => $('#' + id) && ($('#' + id).onchange = reset));
  $('#auX').onclick = () => downloadFile(`/reports/export/auditoria.xlsx?${new URLSearchParams(filters())}`, 'auditoria.xlsx').catch(fail);
  await load();
}
function reportsTab(body) {
  body.innerHTML = `<section class="panel"><div class="filters"><div class="field" style="min-width:300px"><label for="rC">Campanha</label><select id="rC">${campaignOptions(S.campaignId, { allLabel: 'Todas as campanhas' })}</select></div></div>
    <p class="muted">Os arquivos trazem identificação institucional, filtros usados e data de emissão. A ata de apuração (para imprimir ou salvar em PDF) fica na tela Apuração.</p>
    <div class="table-wrap"><table><tbody>${REPORTS.map(([k, t, d]) => `<tr><td><b>${esc(t)}</b><span class="sub">${esc(d)}</span></td><td class="r" style="white-space:nowrap"><button class="btn btn-secondary btn-sm" data-r="${k}" data-f="xlsx">${icon('baixar')}Excel</button> <button class="btn btn-ghost btn-sm" data-r="${k}" data-f="csv">CSV</button></td></tr>`).join('')}
    <tr><td><b>Participações com CPF completo</b><span class="sub">Uso oficial do promotor. A exportação fica registrada na auditoria (LGPD).</span></td><td class="r"><button class="btn btn-ghost btn-sm" id="rFull">CSV</button></td></tr></tbody></table></div></section>`;
  $$('[data-r]', body).forEach((b) => b.onclick = () => {
    const c = $('#rC').value;
    const qs = new URLSearchParams(b.dataset.r === 'auditoria' ? AUDIT_FILTERS : {}); if (c) qs.set('campaign_id', c);
    withLoading(b, () => downloadFile(`/reports/export/${b.dataset.r}.${b.dataset.f}?${qs}`, `${b.dataset.r}.${b.dataset.f}`)).catch(fail);
  });
  $('#rFull').onclick = () => { if (confirm('Este arquivo contém CPF completo dos consumidores. Continuar?')) downloadFile(`/reports/export/participations.csv${$('#rC').value ? `?campaign_id=${$('#rC').value}` : ''}`, 'participacoes.csv').catch(fail); };
}

/* ================================================================== USUÁRIOS */
Pages.usuarios = async (root) => {
  const [users, perms] = await Promise.all([api('/users'), api('/permissionarios')]);
  root.innerHTML = `${pageHead('Usuários', 'Contas de gestores, atendentes do balcão e permissionários. Cada pessoa deve ter a própria conta.')}
    <div class="grid g-side"><div class="table-wrap"><table><thead><tr><th>Usuário</th><th>Perfil</th><th>Último acesso</th><th>Situação</th><th></th></tr></thead><tbody>
    ${users.map((u) => `<tr><td><b>${esc(u.full_name)}</b><span class="sub">${esc(u.username)}${u.permissionario_name ? ' · ' + esc(u.permissionario_name) : ''}${u.is_demo ? ' · conta de demonstração' : ''}</span></td><td>${chip(u.role)}</td><td><small>${fmtDateTime(u.last_login_at)}</small></td>
      <td>${u.is_active ? chip('ATIVO') : chip('INATIVO')}</td><td class="r">${u.id !== S.user.id ? `<button class="btn btn-ghost btn-sm" data-u="${u.id}" data-a="${u.is_active ? 0 : 1}">${u.is_active ? 'Desativar' : 'Reativar'}</button>` : ''}</td></tr>`).join('')}</tbody></table></div>
    <section class="panel"><h2 style="margin-bottom:12px">Nova conta</h2><form id="nu">
      <div class="field"><label for="nuN">Nome completo</label><input id="nuN" required></div>
      <div class="row"><div class="field"><label for="nuU">Usuário</label><input id="nuU" required autocomplete="off"></div><div class="field"><label for="nuP">Senha inicial</label><input id="nuP" type="password" minlength="8" required autocomplete="new-password"></div></div>
      <div class="field"><label for="nuR">Perfil</label><select id="nuR"><option value="ATENDENTE">Atendente do balcão</option><option value="PERMISSIONARIO">Permissionário (portal)</option><option value="ADMIN">Gestor</option></select></div>
      <div class="field" id="nuPermF" hidden><label for="nuPerm">Permissionário</label><select id="nuPerm">${perms.filter((p) => !p.has_portal_user).map((p) => `<option value="${p.id}">${esc(p.name)} — box ${esc(p.boxes.join(', '))}</option>`).join('')}</select></div>
      <button class="btn btn-primary">Criar conta</button></form></section></div>`;
  $('#nuR').onchange = () => { $('#nuPermF').hidden = $('#nuR').value !== 'PERMISSIONARIO'; };
  $('#nu').onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api('/users', { method: 'POST', body: { full_name: $('#nuN').value.trim(), username: $('#nuU').value.trim(), password: $('#nuP').value, role: $('#nuR').value, permissionario_id: $('#nuR').value === 'PERMISSIONARIO' ? +$('#nuPerm').value : null } });
      toast('Conta criada. Entregue o usuário e a senha inicial à pessoa.'); Pages.usuarios(root);
    } catch (err) { fail(err); }
  };
  $$('[data-u]').forEach((b) => b.onclick = async () => {
    try { await api(`/users/${b.dataset.u}/active`, { method: 'POST', body: { is_active: b.dataset.a === '1' } }); toast(b.dataset.a === '1' ? 'Conta reativada.' : 'Conta desativada e sessões encerradas.'); Pages.usuarios(root); } catch (err) { fail(err); }
  });
};

/* ================================================================== GUIA */
Pages.guia = async (root) => {
  const role = S.user.role;
  root.innerHTML = `${pageHead('Guia de uso', 'Como uma campanha acontece do começo ao fim, e o que cada perfil faz em cada etapa.')}
    <div class="guide-flow">
      <div><span class="who">Gestor</span><h3>Criar a campanha</h3><p>Em Campanhas, preencha calendário, regras, prêmios e regulamento. Envie para aprovação.</p>${role === 'ADMIN' ? '<a href="#/campanhas">Abrir Campanhas</a>' : ''}</div>
      <div><span class="who">Gestor + jurídico</span><h3>Aprovar e ativar</h3><p>Registre os seis itens jurídicos e o parecer. Com a campanha aprovada, ative-a.</p></div>
      <div><span class="who">Gestor</span><h3>Conferir boxes</h3><p>Na conferência da planilha, aprove cada box. Quem não está na planilha é cadastrado em Novo permissionário; trocas de titular são feitas pelo mapa. Só boxes confirmados recebem talões.</p>${role === 'ADMIN' ? '<a href="#/permissionarios/conf">Abrir conferência</a>' : ''}</div>
      <div><span class="who">Gestor</span><h3>Distribuir talões</h3><p>Em Talões e comprovantes, gere lotes numerados para cada box. Não há sobreposição de números.</p></div>
      <div><span class="who">Permissionário</span><h3>Entregar comprovantes</h3><p>A cada compra acima do mínimo, entregue um comprovante e registre a entrega no portal.</p>${role === 'PERMISSIONARIO' ? '<a href="#/portal">Abrir Meu box</a>' : ''}</div>
      <div><span class="who">Atendente</span><h3>Validar no balcão</h3><p>Leia o comprovante, identifique o consumidor pelo CPF e gere o número da sorte.</p>${role !== 'PERMISSIONARIO' ? '<a href="#/balcao">Abrir Balcão</a>' : ''}</div>
      <div><span class="who">Gestor</span><h3>Encerrar e congelar</h3><p>Ao fim do prazo, encerre as participações e congele a base. O hash SHA-256 garante que nada mudou depois.</p></div>
      <div><span class="who">Gestor</span><h3>Apurar e entregar</h3><p>Registre a extração da Loteria Federal, emita a ata e acompanhe a entrega do prêmio.</p>${role === 'ADMIN' ? '<a href="#/apuracao">Abrir Apuração</a>' : ''}</div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <section class="panel"><h2 style="margin-bottom:10px">Palavras usadas no sistema</h2><dl class="kv">
        <dt>Talão (lote)</dt><dd style="font-weight:400">Conjunto de comprovantes numerados entregue a um box.</dd>
        <dt>Comprovante</dt><dd style="font-weight:400">Papel com código único (ex.: NATAL-00001) entregue ao consumidor a cada compra.</dd>
        <dt>Número da sorte</dt><dd style="font-weight:400">Número de 5 algarismos gerado no balcão. Cada comprovante gera um único número.</dd>
        <dt>Base congelada</dt><dd style="font-weight:400">Lista final de participações, registrada antes da apuração com uma impressão digital (hash).</dd>
        <dt>Hash SHA-256</dt><dd style="font-weight:400">Código que muda completamente se qualquer participação for alterada. Serve para provar a integridade.</dd>
        <dt>Número apurado</dt><dd style="font-weight:400">Formado pela unidade (último algarismo) do 1º ao 5º prêmio da Loteria Federal.</dd></dl></section>
      <section class="panel"><h2 style="margin-bottom:10px">Mensagens do balcão</h2><table><tbody>
        <tr><td>${chip('VALIDO', 'Válido')}</td><td>Pode prosseguir com o CPF do consumidor.</td></tr>
        <tr><td>${chip('UTILIZADO', 'Já utilizado')}</td><td>O comprovante já gerou um número. Mostra qual e quando.</td></tr>
        <tr><td>${chip('CANCELADO', 'Cancelado')}</td><td>Perdido, devolvido ou cancelado pelo box. Não pode ser usado.</td></tr>
        <tr><td>${chip('BLOQUEADO', 'Permissionário irregular')}</td><td>O box de origem está com cadastro suspenso ou bloqueado.</td></tr>
        <tr><td>${chip('ENCERRADA', 'Campanha encerrada')}</td><td>O prazo de cadastro de comprovantes terminou.</td></tr>
        <tr><td>${chip('SEM_REGISTRO', 'Inexistente')}</td><td>O código não existe. Confira a digitação.</td></tr></tbody></table></section>
    </div>
    ${S.info && S.info.demo_mode ? `<section class="panel" style="margin-top:16px"><h2 style="margin-bottom:8px">Sobre este ambiente de demonstração</h2>
      <p>Todos os dados são <b>fictícios</b> e servem só para conhecer o sistema:</p>
      <ul style="margin:0 0 10px;padding-left:20px">
        <li><b>Campanha Piloto</b> (ativa): 24 boxes com talões, cerca de 230 números da sorte nos últimos 14 dias, recusas e ocorrências.</li>
        <li><b>Dia das Mães 2026</b> (encerrada): base congelada, dois prêmios apurados — um entregue e outro em contato. Use para ver a apuração e emitir a ata.</li>
        <li><b>Volta às Aulas 2027</b> (aguardando aprovação) e <b>Festival do Abacaxi 2027</b> (em elaboração): mostram as etapas pendentes.</li>
        <li>Conferência da planilha: as linhas sem divergência já foram aprovadas; ficaram pendentes as que têm box repetido ou nome em branco.</li>
        <li>Três permissionários estão suspensos para mostrar os bloqueios.</li></ul>
      <p>Os comprovantes <b>NATAL-00001</b> a <b>NATAL-00050</b> do Box 260 estão livres para você testar o balcão. ${S.info.ephemeral_database ? 'Quando o servidor reinicia, tudo volta a este estado inicial.' : ''}</p>
      <p class="muted">Para testar um CPF, use um número válido como 529.982.247-25.</p></section>` : ''}`;
};


/* ================================================================== GESTÃO MANUAL DE BOXES E TITULARES */
let ACTIVITIES = null;
async function activitiesDatalist() {
  if (!ACTIVITIES) ACTIVITIES = await api('/activities');
  return `<datalist id="actList">${ACTIVITIES.map((a) => `<option value="${esc(a)}">`).join('')}</datalist>`;
}
const BOX_ACTION_TXT = { BOX_HOLDER_ASSIGNED: 'Titular vinculado', BOX_HOLDER_TRANSFERRED: 'Troca de titular', BOX_HOLDER_RELEASED: 'Vínculo encerrado', BOX_UPDATED: 'Box alterado' };

/* envia e, se houver comprovantes em aberto do titular anterior, pede confirmação e reenvia */
async function sendWithAck(path, body) {
  try { return await api(path, { method: 'POST', body }); }
  catch (e) {
    if (e.status === 409 && /comprovante/.test(e.message) && confirm(`${e.message}\n\nConfirmar mesmo assim?`)) {
      return api(path, { method: 'POST', body: { ...body, acknowledge_outstanding: true } });
    }
    throw e;
  }
}

async function boxDrawer(number, onChange) {
  const body = openDrawer(`Box ${number}`, loadingBlock(6));
  const reload = () => { boxDrawer(number, onChange); if (onChange) onChange(); };
  try {
    const d = await api(`/boxes/${number}/detail`);
    const c = d.current;
    $('.drawer-head small') && ($('.drawer-head small').textContent = '');
    body.innerHTML = `<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">${chip(d.status)}${c && c.permissionario_status !== 'ATIVO' ? chip(c.permissionario_status, 'Titular ' + statusLabel(c.permissionario_status).toLowerCase()) : ''}</div>
      ${c ? `<dl class="kv"><dt>Titular</dt><dd><a href="javascript:void 0" id="bxPerm">${esc(c.permissionario)}</a></dd><dt>Atividade</dt><dd>${esc(c.activity)}</dd>
        <dt>Desde</dt><dd>${fmtDate(c.since)}</dd><dt>Termo / documento</dt><dd>${esc(c.term || '—')}</dd>
        <dt>Comprovantes em aberto</dt><dd>${fmtN(c.pending_vouchers)}</dd></dl>`
        : `<p class="muted">${d.status === 'SEM_USO' ? 'Box marcado como sem uso.' : 'Este box não tem titular vigente.'}</p>`}
      ${d.sector || d.notes ? `<dl class="kv" style="margin-top:8px">${d.sector ? `<dt>Setor</dt><dd>${esc(d.sector)}</dd>` : ''}${d.notes ? `<dt>Observações</dt><dd style="font-weight:400">${esc(d.notes)}</dd>` : ''}</dl>` : ''}
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:16px">
        ${d.status !== 'SEM_USO' ? `<button class="btn btn-primary" id="bxAssign">${icon('portal')}${c ? 'Trocar titular' : 'Vincular titular'}</button>` : ''}
        ${c ? `<button class="btn btn-secondary" id="bxRelease">Encerrar vínculo</button>` : ''}
        <button class="btn btn-secondary" id="bxEdit">${icon('editar')}Editar box</button>
      </div>
      ${d.staging_rows.some((r) => r.status === 'PENDENTE_REVISAO') ? notice('warn', 'Linha da planilha pendente', `Há ${d.staging_rows.filter((r) => r.status === 'PENDENTE_REVISAO').length} linha(s) da planilha oficial para este box aguardando conferência. <a href="#/permissionarios/conf" id="bxConf">Abrir conferência</a>`) : ''}
      <hr class="divider"><h3>Titulares</h3>
      ${d.holders.length ? `<ul class="timeline">${d.holders.map((h) => `<li><b>${esc(h.permissionario)}</b> — ${esc(h.activity)} ${h.is_current ? chip('ATIVO', 'Vigente') : ''}<small>${fmtDate(h.start_date)}${h.end_date ? ' a ' + fmtDate(h.end_date) : ' até hoje'}${h.term ? ' · ' + esc(h.term) : ''}</small></li>`).join('')}</ul>` : emptyState('Nenhum titular registrado.')}
      <hr class="divider"><h3>Alterações</h3>
      ${d.history.length ? `<ul class="timeline">${d.history.map((h) => { const a = JSON.parse(h.after || '{}'); return `<li><b>${esc(BOX_ACTION_TXT[h.action] || h.action)}</b>${a.holder ? ' — ' + esc(a.holder) : ''}<small>${fmtDateTime(h.timestamp)} · ${esc(h.username)}${a.justification ? ' · ' + esc(a.justification) : ''}</small></li>`; }).join('')}</ul>` : emptyState('Sem alterações manuais.', 'Mudanças feitas pela conferência da planilha aparecem na auditoria.')}`;
    if ($('#bxPerm', body)) $('#bxPerm', body).onclick = () => permDrawer(c.permissionario_id, onChange);
    if ($('#bxConf', body)) $('#bxConf', body).onclick = () => closeOverlay();
    if ($('#bxAssign', body)) $('#bxAssign', body).onclick = () => assignDrawer({ boxNumber: number, current: c, onDone: reload });
    if ($('#bxRelease', body)) $('#bxRelease', body).onclick = () => releaseDrawer(number, c, reload);
    $('#bxEdit', body).onclick = () => editBoxDrawer(d, reload);
  } catch (e) { body.innerHTML = errorBlock(e); }
}

async function assignDrawer({ boxNumber = '', current = null, permissionarioId = null, permissionarioName = '', onDone }) {
  const [perms, dl] = await Promise.all([permissionarioId ? Promise.resolve([]) : api('/permissionarios'), activitiesDatalist()]);
  const title = boxNumber ? (current ? `Trocar titular do Box ${boxNumber}` : `Vincular titular ao Box ${boxNumber}`) : `Vincular ${permissionarioName} a um box`;
  const body = openDrawer(title, `${current ? notice('info', `Titular atual: ${current.permissionario}`, `O vínculo atual será encerrado hoje e ficará no histórico.${current.pending_vouchers ? ` Ele ainda tem <b>${current.pending_vouchers}</b> comprovante(s) em aberto, que continuam válidos em nome dele.` : ''}`) : ''}
    <form id="asg">${dl}
      ${boxNumber ? '' : `<div class="field"><label for="asBox">Número do box</label><input id="asBox" inputmode="numeric" required placeholder="1 a 368"><div class="hint" id="asBoxHint"></div></div>`}
      ${permissionarioId ? '' : `<div class="field"><label for="asPerm">Novo titular</label><input id="asPerm" list="permList" placeholder="Digite para buscar pelo nome" autocomplete="off" required>
        <datalist id="permList">${perms.map((p) => `<option value="${esc(p.name)}">${esc(p.boxes.length ? 'Box ' + p.boxes.join(', ') : 'sem box')} · ${esc(statusLabel(p.status))}</option>`).join('')}</datalist>
        <div class="hint">Não está na lista? <a href="javascript:void 0" id="asNew">Cadastrar novo permissionário</a></div></div>`}
      <div class="field"><label for="asAct">Atividade comercial</label><input id="asAct" list="actList" value="${esc(current ? current.activity : '')}" placeholder="Ex.: MERCEARIA" required></div>
      <div class="field"><label for="asTerm">Termo de permissão / documento <small>(opcional)</small></label><input id="asTerm" placeholder="Ex.: TERMO-2026-045"></div>
      <div class="field"><label for="asJ">Justificativa</label><textarea id="asJ" placeholder="Ex.: Cessão aprovada no processo 77/2026."></textarea></div>
      <button class="btn btn-primary" id="asBtn">${current ? 'Confirmar troca de titular' : 'Vincular titular'}</button></form>`, { modal: true });
  if ($('#asNew', body)) $('#asNew', body).onclick = () => newPermDrawer({ boxNumber, onDone });
  if ($('#asBox', body)) $('#asBox', body).addEventListener('input', debounce(async () => {
    const n = $('#asBox').value.trim(); const hint = $('#asBoxHint');
    if (!/^\d+$/.test(n) || +n < 1 || +n > 368) { hint.textContent = n ? 'O box precisa estar entre 1 e 368.' : ''; return; }
    try { const d = await api(`/boxes/${n}/detail`); hint.textContent = d.current ? `Ocupado por ${d.current.permissionario} — será feita a troca de titular.` : `Situação atual: ${statusLabel(d.status)}.`; if (d.current && !$('#asAct').value) $('#asAct').value = d.current.activity; } catch (_) { hint.textContent = ''; }
  }, 300));
  $('#asg', body).onsubmit = async (e) => {
    e.preventDefault();
    let pid = permissionarioId;
    if (!pid) {
      const name = $('#asPerm').value.trim();
      const match = perms.find((p) => p.name.toLowerCase() === name.toLowerCase());
      if (!match) { toast('Escolha um permissionário da lista ou cadastre um novo.', 'warn'); $('#asPerm').focus(); return; }
      pid = match.id;
    }
    const n = boxNumber || $('#asBox').value.trim();
    const j = $('#asJ').value.trim();
    if (j.length < 5) { $('#asJ').classList.add('invalid'); toast('Informe a justificativa.', 'warn'); return; }
    await withLoading($('#asBtn'), async () => {
      try {
        await sendWithAck(`/boxes/${n}/holder`, { permissionario_id: pid, activity_name: $('#asAct').value.trim(), authorization_term_ref: $('#asTerm').value.trim() || null, justification: j });
        ACTIVITIES = null; closeOverlay(); toast(`Box ${n} vinculado.`); if (onDone) onDone();
      } catch (err) { fail(err); }
    });
  };
}

function releaseDrawer(number, current, onDone) {
  const body = openDrawer(`Encerrar vínculo do Box ${number}`, `<p>O vínculo de <b>${esc(current.permissionario)}</b> será encerrado hoje e ficará no histórico do box. O cadastro do permissionário continua existindo.</p>
    ${current.pending_vouchers ? notice('warn', `${current.pending_vouchers} comprovante(s) em aberto`, 'Eles continuam válidos em nome do permissionário. Se preciso, cancele o lote em Talões e comprovantes.') : ''}
    <form id="rel"><div class="field"><label for="relSt">Nova situação do box</label><select id="relSt"><option value="VAGO_CONFIRMADO">Vago</option><option value="EM_REGULARIZACAO">Em regularização</option><option value="SEM_USO">Sem uso</option></select></div>
    <div class="field"><label for="relJ">Justificativa</label><textarea id="relJ" placeholder="Ex.: Desistência formalizada em 03/11/2026."></textarea></div>
    <button class="btn btn-danger" id="relBtn">Encerrar vínculo</button></form>`, { modal: true });
  $('#rel', body).onsubmit = async (e) => {
    e.preventDefault();
    const j = $('#relJ').value.trim();
    if (j.length < 5) { $('#relJ').classList.add('invalid'); toast('Informe a justificativa.', 'warn'); return; }
    await withLoading($('#relBtn'), async () => {
      try { await sendWithAck(`/boxes/${number}/release`, { target_status: $('#relSt').value, justification: j }); closeOverlay(); toast(`Vínculo do Box ${number} encerrado.`); onDone(); }
      catch (err) { fail(err); }
    });
  };
}

async function editBoxDrawer(d, onDone) {
  const dl = await activitiesDatalist();
  const statuses = d.current ? [['CONFIRMADO', 'Confirmado'], ['EM_REGULARIZACAO', 'Em regularização']] : [['VAGO_CONFIRMADO', 'Vago'], ['EM_REGULARIZACAO', 'Em regularização'], ['SEM_USO', 'Sem uso']];
  const body = openDrawer(`Editar Box ${d.box_number}`, `<form id="eb">${dl}
    <div class="field"><label for="ebSt">Situação</label><select id="ebSt">${statuses.map(([k, l]) => `<option value="${k}" ${d.status === k ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <div class="hint">${d.current ? 'Para deixar o box vago, use "Encerrar vínculo". Boxes em regularização não recebem talões.' : 'Para confirmar o box, vincule um titular.'}</div></div>
    ${d.current ? `<div class="field"><label for="ebAct">Atividade do titular</label><input id="ebAct" list="actList" value="${esc(d.current.activity)}"></div>` : ''}
    <div class="field"><label for="ebSec">Setor <small>(opcional)</small></label><input id="ebSec" value="${esc(d.sector || '')}" placeholder="Ex.: Setor de peixes"></div>
    <div class="field"><label for="ebNotes">Observações</label><textarea id="ebNotes">${esc(d.notes || '')}</textarea></div>
    <div class="field"><label for="ebJ">Justificativa</label><input id="ebJ" placeholder="Ex.: Vistoria do fiscal em 03/11"></div>
    <button class="btn btn-primary" id="ebBtn">Salvar alterações</button></form>`, { modal: true });
  $('#eb', body).onsubmit = async (e) => {
    e.preventDefault();
    const j = $('#ebJ').value.trim();
    if (j.length < 5) { $('#ebJ').classList.add('invalid'); toast('Informe a justificativa.', 'warn'); return; }
    const payload = { official_status: $('#ebSt').value, sector: $('#ebSec').value, notes: $('#ebNotes').value, justification: j };
    if ($('#ebAct') && $('#ebAct').value.trim() !== d.current.activity) payload.activity_name = $('#ebAct').value.trim();
    await withLoading($('#ebBtn'), async () => {
      try { await api(`/boxes/${d.box_number}`, { method: 'PATCH', body: payload }); ACTIVITIES = null; closeOverlay(); toast(`Box ${d.box_number} atualizado.`); onDone(); }
      catch (err) { fail(err); }
    });
  };
}

async function newPermDrawer({ boxNumber = '', onDone } = {}) {
  const dl = await activitiesDatalist();
  const body = openDrawer('Novo permissionário', `<p class="muted">Use para quem não está na planilha oficial — por exemplo, um novo titular assumindo um box vago.</p>
    <form id="np">${dl}
    <div class="field"><label for="npN">Nome completo</label><input id="npN" required></div>
    <div class="row"><div class="field"><label for="npD">CPF ou CNPJ</label><input id="npD" inputmode="numeric"></div>
      <div class="field"><label for="npS">Situação</label><select id="npS"><option value="ATIVO">Ativo</option><option value="SUSPENSO">Suspenso</option><option value="INATIVO">Inativo</option></select></div></div>
    <div class="row"><div class="field"><label for="npP">Telefone</label><input id="npP" inputmode="tel"></div><div class="field"><label for="npE">E-mail</label><input id="npE" type="email"></div></div>
    <hr class="divider"><h3 style="margin-bottom:8px">Box <small class="muted" style="font-family:var(--font-body);font-weight:400">(opcional)</small></h3>
    <div class="row"><div class="field"><label for="npB">Número do box</label><input id="npB" inputmode="numeric" value="${esc(boxNumber)}" placeholder="1 a 368"><div class="hint" id="npBH"></div></div>
      <div class="field"><label for="npA">Atividade</label><input id="npA" list="actList" placeholder="Ex.: VARIEDADES"></div></div>
    <div class="field"><label for="npT">Termo de permissão / documento</label><input id="npT"></div>
    <div class="field"><label for="npJ">Justificativa</label><textarea id="npJ" placeholder="Ex.: Termo de permissão 045/2026 assinado em 01/11/2026."></textarea></div>
    <button class="btn btn-primary" id="npBtn">Cadastrar permissionário</button></form>`);
  maskPhoneInput($('#npP'));
  const checkBox = async () => {
    const n = $('#npB').value.trim(); const h = $('#npBH');
    if (!n) { h.textContent = ''; return; }
    if (!/^\d+$/.test(n) || +n < 1 || +n > 368) { h.textContent = 'O box precisa estar entre 1 e 368.'; return; }
    try { const d = await api(`/boxes/${n}/detail`); h.textContent = d.current ? `Ocupado por ${d.current.permissionario}: será feita a troca de titular.` : `Situação atual: ${statusLabel(d.status)}.`; if (d.current && !$('#npA').value) $('#npA').value = d.current.activity; } catch (_) { h.textContent = ''; }
  };
  $('#npB').addEventListener('input', debounce(checkBox, 300)); if (boxNumber) checkBox();
  $('#np', body).onsubmit = async (e) => {
    e.preventDefault();
    const j = $('#npJ').value.trim();
    if (j.length < 5) { $('#npJ').classList.add('invalid'); toast('Informe a justificativa.', 'warn'); return; }
    if ($('#npB').value.trim() && !$('#npA').value.trim()) { toast('Informe a atividade do box.', 'warn'); $('#npA').focus(); return; }
    const payload = { name: $('#npN').value.trim(), document_cpf_cnpj: $('#npD').value.trim() || null, status: $('#npS').value,
      phone: $('#npP').value.trim() || null, email: $('#npE').value.trim() || null, box_number: $('#npB').value.trim() || null,
      activity_name: $('#npA').value.trim() || null, authorization_term_ref: $('#npT').value.trim() || null, justification: j };
    await withLoading($('#npBtn'), async () => {
      try {
        const r = await sendWithAck('/permissionarios', payload);
        ACTIVITIES = null; closeOverlay(); toast(`${r.name} cadastrado${payload.box_number ? ` no Box ${payload.box_number}` : ''}.`); if (onDone) onDone();
      } catch (err) { fail(err); }
    });
  };
}
