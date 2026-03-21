// ── Copy store ────────────────────────────────────────────────
const _store = new Map();
let _seq = 0;
function reg(text) { const k = ++_seq; _store.set(k, text); return k; }

document.getElementById('panel-body').addEventListener('click', async e => {
  const btn = e.target.closest('.copy-btn');
  if (!btn) return;
  const text = _store.get(+btn.dataset.ck) ?? '';
  await navigator.clipboard.writeText(text);
  btn.classList.add('ok');
  const orig = btn.innerHTML;
  btn.innerHTML = '✓ Copiado';
  setTimeout(() => { btn.classList.remove('ok'); btn.innerHTML = orig; }, 1500);
});

// ── Chain ─────────────────────────────────────────────────────
async function loadChain() {
  const data = await fetch('/api/chain').then(r => r.json());
  renderChain(data);
}

function renderChain(data) {
  document.getElementById('pending-badge').classList.toggle('visible', !!data.pending);
  const el    = document.getElementById('chain');
  const roots = data.roots || [];
  if (!roots.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📂</div><p>No hay CSVs en <strong>data/</strong></p><p>Ejecuta <em>Sync Notion</em> para comenzar.</p></div>';
    return;
  }
  el.innerHTML = roots.map(renderCsvTree).join('');
  updateSelectionUI(); // restore green ring after re-render
}

// Renders a CSV node and all its branches recursively.
// Each branch is { report, output } where output is another CSV subtree (or null).
// Multiple branches from the same CSV are stacked vertically (.chain-fork) so no
// false arrow is ever drawn from a sibling output to an unrelated report.
function renderCsvTree(n) {
  const branches = n.branches || [];
  if (!branches.length) {
    return `<div class="chain-row">${csvNodeHtml(n)}</div>`;
  }
  const fork = branches.map(b => {
    const out = b.output ? `<span class="arrow">→</span>${renderCsvTree(b.output)}` : '';
    return `<div class="chain-branch"><span class="arrow">→</span>${reportNodeHtml(b.report)}${out}</div>`;
  }).join('');
  return `<div class="chain-row">${csvNodeHtml(n)}<div class="chain-fork">${fork}</div></div>`;
}

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function csvNodeHtml(n) {
  const badge = n.pending   ? '<span class="badge badge-pending">⏳ Sin jugar</span>'
              : n.is_latest ? '<span class="badge badge-latest">Actual</span>' : '';
  return `<div class="node node-csv ${n.pending?'latest-pending':''}" data-filename="${esc(n.filename)}" data-type="csv">
    <div class="node-icon">📋</div><div class="node-label">CSV</div>
    <div class="node-name">${esc(n.filename)}</div>
    <div class="node-meta">${n.player_count} jugadores</div>${badge}</div>`;
}

function reportNodeHtml(n) {
  const date = (n.generated||'').split(' ')[0];
  const time = (n.generated||'').split(' ')[1] ?? '';
  return `<div class="node node-report" data-filename="${esc(n.filename)}" data-type="report">
    <div class="node-icon">📊</div><div class="node-label">Reporte</div>
    <div class="node-name">${esc(date)}</div>
    <div class="node-meta">${esc(time)}<br>${esc(n.partidas)}<br>${esc(n.en_espera)}</div></div>`;
}

// ── Node click ────────────────────────────────────────────────
document.getElementById('chain').addEventListener('click', e => {
  const node = e.target.closest('.node');
  if (!node) return;
  const fn   = node.dataset.filename;
  const type = node.dataset.type;
  setActive(fn);
  if (type === 'csv') {
    setSelectedCsv(fn);
    openCSV(fn);
  } else {
    openReport(fn);
  }
});

function setActive(fn) {
  document.querySelectorAll('.node').forEach(n => n.classList.remove('active'));
  const el = document.querySelector(`[data-filename="${CSS.escape(fn)}"]`);
  if (el) el.classList.add('active');
}

// ── CSV selection (source for Organizar) ─────────────────────
// _selectedCsv is null → server uses the latest CSV.
// Clicking a CSV node selects it; ✕ button deselects.
// Sync Notion is ALWAYS a fresh pull from Notion — it ignores the selected CSV.
let _selectedCsv = null;

function setSelectedCsv(filename) {
  _selectedCsv = filename;
  updateSelectionUI();
}

function deselectCsv() {
  _selectedCsv = null;
  updateSelectionUI();
}

function updateSelectionUI() {
  document.querySelectorAll('.node-csv').forEach(n =>
    n.classList.toggle('csv-selected', n.dataset.filename === _selectedCsv)
  );
  const label    = document.getElementById('organizar-label');
  const deselBtn = document.getElementById('btn-deselect');
  if (_selectedCsv) {
    const num = _selectedCsv.replace('jugadores_', '').replace('.csv', '');
    label.textContent      = `Organizar · ${num}`;
    deselBtn.style.display = '';
  } else {
    label.textContent      = 'Organizar';
    deselBtn.style.display = 'none';
  }
}

function runOrganizar() {
  runScript('organizar', _selectedCsv); // null → server picks the latest CSV
}

// ── Panel ─────────────────────────────────────────────────────
function openPanel(title) {
  document.getElementById('panel-title').textContent = title;
  document.getElementById('panel-body').innerHTML = '<p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>';
  document.getElementById('panel').classList.add('open');
}

function closePanel() {
  document.getElementById('panel').classList.remove('open');
  document.querySelectorAll('.node').forEach(n => n.classList.remove('active'));
}

// ── CSV panel ─────────────────────────────────────────────────
async function openCSV(filename) {
  openPanel(filename);
  const data = await fetch(`/api/csv/${encodeURIComponent(filename)}`).then(r => r.json());
  const rows   = data.rows ?? [];
  const cols   = ['Nombre','Experiencia','Juegos_Este_Ano','Prioridad','Partidas_Deseadas','Partidas_GM'];
  const labels = {Nombre:'Nombre',Experiencia:'Exp.',Juegos_Este_Ano:'Juegos',Prioridad:'Prior.',Partidas_Deseadas:'Desea',Partidas_GM:'GM'};
  const csvTxt = [cols.join(','), ...rows.map(r => cols.map(c => r[c]??'').join(','))].join('\n');
  const ck = reg(csvTxt);
  const tbody = rows.map(r => '<tr>' + cols.map(c => {
    let v = esc(r[c]??'');
    if (c==='Experiencia') {
      const color = r[c]==='Nuevo' ? '#713f12' : '#166534';
      const bg    = r[c]==='Nuevo' ? '#fef9c3' : '#f0fdf4';
      v = `<span style="font-size:10px;font-weight:700;color:${color};background:${bg};padding:1px 6px;border-radius:4px">${esc(r[c])}</span>`;
    }
    if (c==='Prioridad') v = r[c]==='True' ? '✓' : '';
    return `<td>${v}</td>`;
  }).join('') + '</tr>').join('');
  document.getElementById('panel-body').innerHTML = `
    <div class="section"><div class="section-title">Jugadores (${rows.length})</div>
      <button class="copy-btn" data-ck="${ck}">📋 Copiar tabla CSV</button></div>
    <div class="section"><div class="table-wrap"><table>
      <thead><tr>${cols.map(c=>`<th>${labels[c]}</th>`).join('')}</tr></thead>
      <tbody>${tbody}</tbody>
    </table></div></div>`;
}

// ── Report panel ──────────────────────────────────────────────
async function openReport(filename) {
  openPanel(filename);
  const data     = await fetch(`/api/report/${encodeURIComponent(filename)}`).then(r => r.json());
  const reg_data = data.registro ?? {};
  const mesas    = data.detalle?.mesas ?? [];
  const waiting  = data.detalle?.waiting_list ?? [];
  const copyText = data.copypaste ?? '';
  document.getElementById('panel-title').textContent = reg_data['Generado'] ?? filename;
  let html = '';
  html += '<div class="section"><div class="section-title">Resumen</div><div class="meta-grid">';
  for (const [k, v] of Object.entries(reg_data))
    html += `<span class="meta-key">${esc(k)}</span><span class="meta-val">${esc(v)}</span>`;
  html += '</div></div>';
  const ckShare = reg(copyText);
  html += `<div class="section">
    <button class="copy-btn" data-ck="${ckShare}">📋 Copiar lista para compartir</button>
    <div class="share-pre" style="margin-top:8px">${esc(copyText)}</div>
  </div>`;
  if (mesas.length) {
    html += `<div class="section"><div class="section-title">Partidas (${mesas.length})</div>`;
    for (const mesa of mesas) {
      const gmTag = mesa.gm
        ? `<span class="gm-tag gm-tag-ok">GM: ${esc(mesa.gm)}</span>`
        : '<span class="gm-tag gm-tag-bad">⚠️ Sin GM</span>';
      const playersTxt = mesa.jugadores.map(j => j.nombre).join('\n');
      const ckMesa = reg(playersTxt);
      const playerRows = mesa.jugadores.map((j, i) => {
        const tag = j.etiqueta === 'Nuevo'
          ? '<span class="tag tag-nuevo">Nuevo</span>'
          : `<span class="tag tag-antiguo">${esc(j.etiqueta)}</span>`;
        return `<li><span class="p-num">${i+1}.</span><span class="p-name">${esc(j.nombre)}</span>${tag}</li>`;
      }).join('');
      html += `<div class="mesa-card">
        <div class="mesa-header"><span class="mesa-title">Partida ${mesa.numero}</span>${gmTag}</div>
        <ul class="player-list">${playerRows}</ul>
        <button class="copy-btn" data-ck="${ckMesa}" style="margin-top:9px">📋 Copiar jugadores</button>
      </div>`;
    }
    html += '</div>';
  }
  if (waiting.length) {
    const waitTxt = waiting.map(w => w.nombre).join('\n');
    const ckWait  = reg(waitTxt);
    html += `<div class="section"><div class="section-title">Lista de espera</div>
      ${waiting.map(w => `<div class="waiting-item">
        <span class="waiting-name">${esc(w.nombre)}</span>
        <span class="waiting-cupos">${esc(w.cupos)}</span>
      </div>`).join('')}
      <button class="copy-btn" data-ck="${ckWait}">📋 Copiar lista de espera</button>
    </div>`;
  }
  document.getElementById('panel-body').innerHTML = html;
}

// ── Run scripts ───────────────────────────────────────────────
const scriptLabels = { notion_sync: '↻ Sync Notion', organizar: '▶ Organizar' };

async function runScript(script, csvName = null) {
  const modal    = document.getElementById('modal');
  const out      = document.getElementById('modal-out');
  const titleEl  = document.getElementById('modal-title-text');
  const iconEl   = document.getElementById('modal-icon');
  const closeBtn = document.getElementById('btn-modal-close');
  out.textContent = ''; out.className = 'modal-out';
  titleEl.textContent = `Ejecutando ${scriptLabels[script]}…`;
  iconEl.innerHTML = '<span class="spinner"></span>';
  closeBtn.disabled = true;
  modal.classList.add('open');
  document.getElementById('btn-sync').disabled      = true;
  document.getElementById('btn-organizar').disabled = true;
  const body = (script === 'organizar' && csvName) ? { csv: csvName } : undefined;
  try {
    const res  = await fetch(`/api/run/${script}`, {
      method:  'POST',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body:    body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json();
    const ok   = data.returncode === 0;
    iconEl.textContent  = ok ? '✅' : '❌';
    titleEl.textContent = ok ? `${scriptLabels[script]} completado` : `Error en ${scriptLabels[script]}`;
    out.textContent     = (data.stdout??'') + (data.stderr ? '\n[stderr]\n'+data.stderr : '');
    if (!ok) out.classList.add('err');
    if (ok)  await loadChain();
  } catch (e) {
    iconEl.textContent  = '❌';
    titleEl.textContent = 'Error de conexión';
    out.textContent     = String(e);
    out.classList.add('err');
  } finally {
    closeBtn.disabled = false;
    document.getElementById('btn-sync').disabled      = false;
    document.getElementById('btn-organizar').disabled = false;
  }
}

function closeModal() { document.getElementById('modal').classList.remove('open'); }

loadChain();
