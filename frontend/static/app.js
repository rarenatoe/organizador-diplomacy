(() => {
  // frontend/src/selection.ts
  var _selectedSnapshot = null;
  function getSelectedSnapshot() {
    return _selectedSnapshot;
  }
  function setSelectedSnapshot(id) {
    _selectedSnapshot = id;
    updateSelectionUI();
  }
  function deselectSnapshot() {
    _selectedSnapshot = null;
    updateSelectionUI();
  }
  function updateSelectionUI() {
    document.querySelectorAll(".node-csv").forEach((n) => {
      const nodeId = parseInt(n.dataset["id"] ?? "", 10);
      n.classList.toggle("csv-selected", nodeId === _selectedSnapshot);
    });
    const label = document.getElementById("organizar-label");
    const deselBtn = document.getElementById("btn-deselect");
    if (_selectedSnapshot !== null) {
      label.textContent = `Organizar · #${_selectedSnapshot}`;
      deselBtn.style.display = "";
    } else {
      label.textContent = "Organizar";
      deselBtn.style.display = "none";
    }
  }

  // frontend/src/chain.ts
  function esc(s) {
    const str = s ?? "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  async function loadChain() {
    const data = await fetch("/api/chain").then((r) => r.json());
    renderChain(data);
  }
  function renderChain(data) {
    const el = document.getElementById("chain");
    const roots = data.roots ?? [];
    if (!roots.length) {
      el.innerHTML = '<div class="empty-state"><div class="icon">\uD83D\uDCC2</div><p>No hay snapshots en la DB.</p><p>Ejecuta <em>Sync Notion</em> para comenzar.</p></div>';
      return;
    }
    el.innerHTML = roots.map(renderSnapshotTree).join("");
    updateSelectionUI();
  }
  function renderSnapshotTree(n) {
    const branches = n.branches ?? [];
    if (!branches.length) {
      return `<div class="chain-row">${snapshotNodeHtml(n)}</div>`;
    }
    const fork = branches.map((b) => {
      const edgeHtml = b.edge.type === "sync" ? syncNodeHtml(b.edge) : gameNodeHtml(b.edge);
      const out = b.output ? `<span class="arrow">→</span>${renderSnapshotTree(b.output)}` : "";
      return `<div class="chain-branch"><span class="arrow">→</span>${edgeHtml}${out}</div>`;
    }).join("");
    return `<div class="chain-row">${snapshotNodeHtml(n)}<div class="chain-fork">${fork}</div></div>`;
  }
  function snapshotNodeHtml(n) {
    const badge = n.is_latest ? '<span class="badge badge-latest">Actual</span>' : "";
    const sourceLabel = n.source === "notion_sync" ? "☁️ Notion Sync" : n.source === "organizar" ? "▶ Organizar" : "\uD83D\uDCE5 Manual";
    return `<div class="node node-csv" data-id="${n.id}" data-type="snapshot">
    <button class="node-delete-btn" data-snapshot-id="${n.id}" title="Eliminar snapshot">\uD83D\uDDD1</button>
    <div class="node-icon">\uD83D\uDCCB</div><div class="node-label">Snapshot #${n.id}</div>
    <div class="node-name">${esc(n.created_at)}</div>
    <div class="node-meta">${n.player_count} jugadores · ${sourceLabel}</div>${badge}</div>`;
  }
  function gameNodeHtml(n) {
    const date = (n.created_at || "").split(" ")[0] ?? "";
    const time = (n.created_at || "").split(" ")[1] ?? "";
    return `<div class="node node-report" data-id="${n.id}" data-type="game">
    <div class="node-icon">\uD83D\uDCCA</div><div class="node-label">Jornada</div>
    <div class="node-name">${esc(date)}</div>
    <div class="node-meta">${esc(time)}<br>${n.mesa_count} partida(s)<br>${n.espera_count} en espera</div></div>`;
  }
  function syncNodeHtml(n) {
    const date = (n.created_at || "").split(" ")[0] ?? "";
    return `<div class="node node-sync"
    data-id="${n.id}"
    data-type="sync">
    <div class="node-icon">☁️</div><div class="node-label">Sync Notion</div>
    <div class="node-name">${esc(date)}</div>
    <div class="node-meta">#${n.from_id} → #${n.to_id}</div></div>`;
  }

  // frontend/src/clipboard.ts
  var _store = new Map;
  var _seq = 0;
  function reg(text) {
    const k = ++_seq;
    _store.set(k, text);
    return k;
  }
  document.getElementById("panel-body").addEventListener("click", (e) => {
    const btn = e.target.closest(".copy-btn");
    if (btn) {
      const ckStr = btn.dataset["ck"];
      const text = _store.get(+(ckStr ?? "0")) ?? "";
      navigator.clipboard.writeText(text).then(() => {
        btn.classList.add("ok");
        const orig = btn.innerHTML;
        btn.innerHTML = "✓ Copiado";
        setTimeout(() => {
          btn.classList.remove("ok");
          btn.innerHTML = orig;
        }, 1500);
      });
    }
  });

  // frontend/src/panels.ts
  function openPanel(title) {
    document.getElementById("panel-title").textContent = title;
    document.getElementById("panel-body").innerHTML = '<p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>';
    document.getElementById("panel").classList.add("open");
  }
  function closePanel() {
    document.getElementById("panel").classList.remove("open");
    document.querySelectorAll(".node").forEach((n) => {
      n.classList.remove("active");
    });
  }
  document.getElementById("panel-body").addEventListener("change", (e) => {
    const cb = e.target.closest(".player-keep");
    if (!cb)
      return;
    const tr = cb.closest("tr");
    if (tr)
      tr.classList.toggle("excluded", !cb.checked);
  });
  async function openSnapshot(id) {
    openPanel(`Snapshot #${id}`);
    const data = await fetch(`/api/snapshot/${id}`).then((r) => r.json());
    const rows = data.players ?? [];
    const CSV_COLS = [
      "nombre",
      "experiencia",
      "juegos_este_ano",
      "prioridad",
      "partidas_deseadas",
      "partidas_gm"
    ];
    const csvTxt = [
      CSV_COLS.join(","),
      ...rows.map((r) => CSV_COLS.map((c) => String(r[c])).join(","))
    ].join(`
`);
    const ck = reg(csvTxt);
    const sourceLabel = data.source === "notion_sync" ? "☁️ Notion Sync" : data.source === "organizar" ? "▶ Organizar" : "\uD83D\uDCE5 Manual";
    const editRows = rows.map((r) => {
      const checked = r["prioridad"] === 1 ? "checked" : "";
      const gmChecked = r["partidas_gm"] > 0 ? "checked" : "";
      const nombre = esc(String(r["nombre"] ?? ""));
      const expColor = r["experiencia"] === "Nuevo" ? "#713f12" : "#166534";
      const expBg = r["experiencia"] === "Nuevo" ? "#fef9c3" : "#f0fdf4";
      const expBadge = `<span style="font-size:10px;font-weight:700;color:${expColor};background:${expBg};padding:1px 6px;border-radius:4px">${esc(String(r["experiencia"] ?? ""))}</span>`;
      return `<tr data-nombre="${nombre}">
        <td><input type="checkbox" class="player-keep" checked title="Incluir"></td>
        <td>${nombre}</td>
        <td>${expBadge}</td>
        <td>${String(r["juegos_este_ano"] ?? "")}</td>
        <td><input type="checkbox" class="player-prio" ${checked}></td>
        <td><input type="number" class="player-deseadas" value="${String(r["partidas_deseadas"] ?? "1")}" min="1" max="9" style="width:38px"></td>
        <td><input type="checkbox" class="player-gm" ${gmChecked}></td>
      </tr>`;
    }).join("");
    document.getElementById("panel-body").innerHTML = `
    <div class="section"><div class="section-title">Snapshot #${id} · ${sourceLabel}</div>
      <div class="node-meta" style="margin-bottom:8px">${esc(data.created_at)}</div>
      <button class="copy-btn" data-ck="${ck}">\uD83D\uDCCB Copiar tabla CSV</button></div>
    <div class="section">
      <div class="section-title" style="margin-bottom:6px">Jugadores <span style="color:var(--muted);font-weight:400;text-transform:none;font-size:11px">— desactiva para excluir de la siguiente jornada</span></div>
      <div class="table-wrap"><table id="snapshot-edit-table">
        <thead><tr><th></th><th>Nombre</th><th>Exp.</th><th>Juegos</th><th>Prior.</th><th>Desea</th><th>GM</th></tr></thead>
        <tbody>${editRows}</tbody>
      </table></div>
    </div>
    <div class="section">
      <button class="btn btn-primary" id="btn-apply-edit" style="width:100%">✨ Crear snapshot manual con estos ajustes</button>
    </div>`;
    document.getElementById("btn-apply-edit").addEventListener("click", () => {
      applySnapshotEdit(id);
    });
  }
  async function applySnapshotEdit(sourceId) {
    const table = document.getElementById("snapshot-edit-table");
    if (!table)
      return;
    const players = [];
    table.querySelectorAll("tbody tr").forEach((tr) => {
      const keep = tr.querySelector(".player-keep");
      if (!keep?.checked)
        return;
      const nombre = tr.dataset["nombre"] ?? "";
      const prio = tr.querySelector(".player-prio");
      const deseadas = tr.querySelector(".player-deseadas");
      const gm = tr.querySelector(".player-gm");
      players.push({
        nombre,
        prioridad: prio?.checked ? 1 : 0,
        partidas_deseadas: parseInt(deseadas?.value ?? "1", 10),
        partidas_gm: gm?.checked ? 1 : 0
      });
    });
    const btn = document.getElementById("btn-apply-edit");
    btn.disabled = true;
    btn.textContent = "Creando…";
    try {
      const res = await fetch(`/api/snapshot/${sourceId}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ players })
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`Error: ${data.error ?? res.status}`);
        btn.disabled = false;
        btn.textContent = "✨ Crear snapshot manual con estos ajustes";
        return;
      }
      closePanel();
      await loadChain();
      const newId = data.snapshot_id;
      if (newId !== undefined) {
        setSelectedSnapshot(newId);
        openSnapshot(newId);
      }
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
      btn.disabled = false;
      btn.textContent = "✨ Crear snapshot manual con estos ajustes";
    }
  }
  async function openSyncPanel(id) {
    openPanel("Sync Notion");
    const chain = await fetch("/api/chain").then((r) => r.json());
    const found = { val: null };
    function findSync(roots) {
      for (const root of roots) {
        for (const branch of root.branches ?? []) {
          if (branch.edge.type === "sync" && branch.edge.id === id) {
            found.val = {
              from_id: branch.edge.from_id,
              to_id: branch.edge.to_id,
              created_at: branch.edge.created_at
            };
          }
          if (branch.output)
            findSync([branch.output]);
        }
      }
    }
    findSync(chain.roots ?? []);
    const info = found.val;
    if (info !== null) {
      const { from_id, to_id, created_at } = info;
      document.getElementById("panel-body").innerHTML = `
      <div class="section">
        <div class="section-title">Detalles del Sync</div>
        <div class="meta-grid">
          <span class="meta-key">Generado</span><span class="meta-val">${esc(created_at)}</span>
          <span class="meta-key">De snapshot</span><span class="meta-val">#${from_id}</span>
          <span class="meta-key">A snapshot</span><span class="meta-val">#${to_id}</span>
        </div>
      </div>`;
    } else {
      document.getElementById("panel-body").innerHTML = "<p>Sync no encontrado.</p>";
    }
  }
  async function openGame(id) {
    openPanel(`Jornada #${id}`);
    const data = await fetch(`/api/game/${id}`).then((r) => r.json());
    const mesas = data.mesas ?? [];
    const waiting = data.waiting_list ?? [];
    const copyText = data.copypaste;
    document.getElementById("panel-title").textContent = data.created_at;
    let html = "";
    html += `<div class="section"><div class="section-title">Resumen</div><div class="meta-grid">
    <span class="meta-key">Generado</span><span class="meta-val">${esc(data.created_at)}</span>
    <span class="meta-key">Intentos</span><span class="meta-val">${data.intentos}</span>
    <span class="meta-key">Snapshot entrada</span><span class="meta-val">#${data.input_snapshot_id}</span>
    <span class="meta-key">Snapshot salida</span><span class="meta-val">#${data.output_snapshot_id}</span>
  </div></div>`;
    const ckShare = reg(copyText);
    html += `<div class="section">
    <button class="copy-btn" data-ck="${ckShare}">\uD83D\uDCCB Copiar lista para compartir</button>
    <div class="share-pre" style="margin-top:8px">${esc(copyText)}</div>
  </div>`;
    if (mesas.length) {
      html += `<div class="section"><div class="section-title">Partidas (${mesas.length})</div>`;
      for (const mesa of mesas) {
        const gmTag = mesa.gm ? `<span class="gm-tag gm-tag-ok">GM: ${esc(mesa.gm)}</span>` : '<span class="gm-tag gm-tag-bad">⚠️ Sin GM</span>';
        const playersTxt = mesa.jugadores.map((j) => j.nombre).join(`
`);
        const ckMesa = reg(playersTxt);
        const playerRows = mesa.jugadores.map((j, i) => {
          const tag = j.etiqueta === "Nuevo" ? '<span class="tag tag-nuevo">Nuevo</span>' : `<span class="tag tag-antiguo">${esc(j.etiqueta)}</span>`;
          return `<li><span class="p-num">${i + 1}.</span><span class="p-name">${esc(j.nombre)}</span>${tag}</li>`;
        }).join("");
        html += `<div class="mesa-card">
        <div class="mesa-header"><span class="mesa-title">Partida ${mesa.numero}</span>${gmTag}</div>
        <ul class="player-list">${playerRows}</ul>
        <button class="copy-btn" data-ck="${ckMesa}" style="margin-top:9px">\uD83D\uDCCB Copiar jugadores</button>
      </div>`;
      }
      html += "</div>";
    }
    if (waiting.length) {
      const waitTxt = waiting.map((w) => w.nombre).join(`
`);
      const ckWait = reg(waitTxt);
      html += `<div class="section"><div class="section-title">Lista de espera</div>
      ${waiting.map((w) => `<div class="waiting-item">
        <span class="waiting-name">${esc(w.nombre)}</span>
        <span class="waiting-cupos">${esc(w.cupos)}</span>
      </div>`).join("")}
      <button class="copy-btn" data-ck="${ckWait}">\uD83D\uDCCB Copiar lista de espera</button>
    </div>`;
    }
    document.getElementById("panel-body").innerHTML = html;
  }
  async function deleteSnapshot(id) {
    if (!confirm(`¿Eliminar snapshot #${id} y todos sus descendientes?
Esta acción no se puede deshacer.`))
      return;
    try {
      const res = await fetch(`/api/snapshot/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        alert(`Error al eliminar: ${err.error ?? res.status}`);
        return;
      }
      const data = await res.json();
      const sel = getSelectedSnapshot();
      if (sel !== null && data.deleted.includes(sel)) {
        deselectSnapshot();
      }
      closePanel();
      await loadChain();
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    }
  }

  // frontend/src/app.ts
  document.getElementById("chain").addEventListener("click", (e) => {
    const delBtn = e.target.closest(".node-delete-btn");
    if (delBtn) {
      const id2 = parseInt(delBtn.dataset["snapshotId"] ?? "", 10);
      deleteSnapshot(id2);
      return;
    }
    const node = e.target.closest(".node");
    if (!node)
      return;
    const idStr = node.dataset["id"] ?? "";
    const id = parseInt(idStr, 10);
    const type = node.dataset["type"];
    setActive(idStr);
    if (type === "snapshot") {
      setSelectedSnapshot(id);
      openSnapshot(id);
    } else if (type === "sync") {
      openSyncPanel(id);
    } else if (type === "game") {
      openGame(id);
    }
  });
  function setActive(idStr) {
    document.querySelectorAll(".node").forEach((n) => {
      n.classList.remove("active");
    });
    const el = document.querySelector(`[data-id="${CSS.escape(idStr)}"]`);
    if (el)
      el.classList.add("active");
  }
  var SCRIPT_LABELS = {
    notion_sync: "↻ Sync Notion",
    organizar: "▶ Organizar"
  };
  async function runScript(script, snapshotId = null) {
    const modal = document.getElementById("modal");
    const out = document.getElementById("modal-out");
    const titleEl = document.getElementById("modal-title-text");
    const iconEl = document.getElementById("modal-icon");
    const closeBtn = document.getElementById("btn-modal-close");
    const btnSync = document.getElementById("btn-sync");
    const btnOrganizar = document.getElementById("btn-organizar");
    out.textContent = "";
    out.className = "modal-out";
    titleEl.textContent = `Ejecutando ${SCRIPT_LABELS[script] ?? script}…`;
    iconEl.innerHTML = '<span class="spinner"></span>';
    closeBtn.disabled = true;
    modal.classList.add("open");
    btnSync.disabled = true;
    btnOrganizar.disabled = true;
    const fetchInit = { method: "POST" };
    if (snapshotId !== null) {
      fetchInit.headers = { "Content-Type": "application/json" };
      fetchInit.body = JSON.stringify({ snapshot: snapshotId });
    }
    try {
      const res = await fetch(`/api/run/${script}`, fetchInit);
      const data = await res.json();
      const ok = data.returncode === 0;
      iconEl.textContent = ok ? "✅" : "❌";
      titleEl.textContent = ok ? `${SCRIPT_LABELS[script] ?? script} completado` : `Error en ${SCRIPT_LABELS[script] ?? script}`;
      out.textContent = (data.stdout ?? "") + (data.stderr ? `
[stderr]
` + data.stderr : "");
      if (!ok)
        out.classList.add("err");
      if (ok)
        await loadChain();
    } catch (e) {
      iconEl.textContent = "❌";
      titleEl.textContent = "Error de conexión";
      out.textContent = String(e);
      out.classList.add("err");
    } finally {
      closeBtn.disabled = false;
      btnSync.disabled = false;
      btnOrganizar.disabled = false;
    }
  }
  function closeModal() {
    document.getElementById("modal").classList.remove("open");
  }
  document.getElementById("btn-refresh").addEventListener("click", () => {
    loadChain();
  });
  document.getElementById("btn-sync").addEventListener("click", () => {
    runScript("notion_sync", getSelectedSnapshot());
  });
  document.getElementById("btn-organizar").addEventListener("click", () => {
    runScript("organizar", getSelectedSnapshot());
  });
  document.getElementById("btn-deselect").addEventListener("click", deselectSnapshot);
  document.getElementById("btn-close-panel").addEventListener("click", closePanel);
  document.getElementById("btn-modal-close").addEventListener("click", closeModal);
  loadChain();
})();
