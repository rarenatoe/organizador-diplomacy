import type {
  SnapshotNode,
  GameEdge,
  SyncEdge,
  ChainData,
  RunResult,
  SnapshotDetail,
  GameDetail,
} from "./types";

// ── Copy store ────────────────────────────────────────────────────────────────

const _store = new Map<number, string>();
let _seq = 0;

function reg(text: string): number {
  const k = ++_seq;
  _store.set(k, text);
  return k;
}

document
  .getElementById("panel-body")!
  .addEventListener("click", (e: MouseEvent) => {
    const btn = (e.target as Element).closest<HTMLElement>(".copy-btn");
    if (!btn) return;
    const ckStr = btn.dataset["ck"];
    const text = _store.get(+(ckStr ?? "0")) ?? "";
    void navigator.clipboard.writeText(text).then(() => {
      btn.classList.add("ok");
      const orig = btn.innerHTML;
      btn.innerHTML = "✓ Copiado";
      setTimeout(() => {
        btn.classList.remove("ok");
        btn.innerHTML = orig;
      }, 1500);
    });
  });

// ── Chain ─────────────────────────────────────────────────────────────────────

async function loadChain(): Promise<void> {
  const data = (await fetch("/api/chain").then((r) => r.json())) as ChainData;
  renderChain(data);
}

function renderChain(data: ChainData): void {
  const el = document.getElementById("chain")!;
  const roots = data.roots ?? [];
  if (!roots.length) {
    el.innerHTML =
      '<div class="empty-state"><div class="icon">📂</div><p>No hay snapshots en la DB.</p><p>Ejecuta <em>Sync Notion</em> para comenzar.</p></div>';
    return;
  }
  el.innerHTML = roots.map(renderSnapshotTree).join("");
  updateSelectionUI(); // restore green ring after re-render
}

// Renders a snapshot node and all its branches recursively.
function renderSnapshotTree(n: SnapshotNode): string {
  const branches = n.branches ?? [];
  if (!branches.length) {
    return `<div class="chain-row">${snapshotNodeHtml(n)}</div>`;
  }
  const fork = branches
    .map((b) => {
      const edgeHtml =
        b.edge.type === "sync" ? syncNodeHtml(b.edge) : gameNodeHtml(b.edge);
      const out = b.output
        ? `<span class="arrow">→</span>${renderSnapshotTree(b.output)}`
        : "";
      return `<div class="chain-branch"><span class="arrow">→</span>${edgeHtml}${out}</div>`;
    })
    .join("");
  return `<div class="chain-row">${snapshotNodeHtml(n)}<div class="chain-fork">${fork}</div></div>`;
}

function esc(s: string | null | undefined): string {
  const str = s ?? "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function snapshotNodeHtml(n: SnapshotNode): string {
  const badge = n.is_latest
    ? '<span class="badge badge-latest">Actual</span>'
    : "";
  const sourceLabel =
    n.source === "notion_sync"
      ? "☁️ Notion Sync"
      : n.source === "organizar"
        ? "▶ Organizar"
        : "📥 Manual";
  return `<div class="node node-csv" data-id="${n.id}" data-type="snapshot">
    <div class="node-icon">📋</div><div class="node-label">Snapshot #${n.id}</div>
    <div class="node-name">${esc(n.created_at)}</div>
    <div class="node-meta">${n.player_count} jugadores · ${sourceLabel}</div>${badge}</div>`;
}

function gameNodeHtml(n: GameEdge): string {
  const date = (n.created_at || "").split(" ")[0] ?? "";
  const time = (n.created_at || "").split(" ")[1] ?? "";
  return `<div class="node node-report" data-id="${n.id}" data-type="game">
    <div class="node-icon">📊</div><div class="node-label">Partida</div>
    <div class="node-name">${esc(date)}</div>
    <div class="node-meta">${esc(time)}<br>${n.mesa_count} mesa(s)<br>${n.espera_count} en espera</div></div>`;
}

function syncNodeHtml(n: SyncEdge): string {
  const date = (n.created_at || "").split(" ")[0] ?? "";
  return `<div class="node node-sync"
    data-id="${n.id}"
    data-type="sync">
    <div class="node-icon">☁️</div><div class="node-label">Sync Notion</div>
    <div class="node-name">${esc(date)}</div>
    <div class="node-meta">#${n.from_id} → #${n.to_id}</div></div>`;
}

// ── Node click ─────────────────────────────────────────────────────────────────

document.getElementById("chain")!.addEventListener("click", (e: MouseEvent) => {
  const node = (e.target as Element).closest<HTMLElement>(".node");
  if (!node) return;
  const idStr = node.dataset["id"] ?? "";
  const id = parseInt(idStr, 10);
  const type = node.dataset["type"];
  setActive(idStr);
  if (type === "snapshot") {
    setSelectedSnapshot(id);
    void openSnapshot(id);
  } else if (type === "sync") {
    void openSyncPanel(id);
  } else if (type === "game") {
    void openGame(id);
  }
});

function setActive(idStr: string): void {
  document.querySelectorAll<HTMLElement>(".node").forEach((n) => {
    n.classList.remove("active");
  });
  const el = document.querySelector<HTMLElement>(
    `[data-id="${CSS.escape(idStr)}"]`,
  );
  if (el) el.classList.add("active");
}

// ── Snapshot selection (source for Organizar) ─────────────────────────────────
// _selectedSnapshot is null → server uses the latest snapshot.
// Clicking a snapshot node selects it; ✕ button deselects.
// Sync Notion is ALWAYS a fresh pull from Notion — it ignores the selected snapshot.

let _selectedSnapshot: number | null = null;

function setSelectedSnapshot(id: number): void {
  _selectedSnapshot = id;
  updateSelectionUI();
}

function deselectSnapshot(): void {
  _selectedSnapshot = null;
  updateSelectionUI();
}

// Keep backwards-compat alias used by button handler
const deselectCsv = deselectSnapshot;

function updateSelectionUI(): void {
  document.querySelectorAll<HTMLElement>(".node-csv").forEach((n) => {
    const nodeId = parseInt(n.dataset["id"] ?? "", 10);
    n.classList.toggle("csv-selected", nodeId === _selectedSnapshot);
  });
  const label = document.getElementById("organizar-label")!;
  const deselBtn = document.getElementById("btn-deselect") as HTMLElement;
  if (_selectedSnapshot !== null) {
    label.textContent = `Organizar · #${_selectedSnapshot}`;
    deselBtn.style.display = "";
  } else {
    label.textContent = "Organizar";
    deselBtn.style.display = "none";
  }
}

function runOrganizar(): void {
  void runScript("organizar", _selectedSnapshot);
}

// ── Panel ─────────────────────────────────────────────────────────────────────

function openPanel(title: string): void {
  document.getElementById("panel-title")!.textContent = title;
  document.getElementById("panel-body")!.innerHTML =
    '<p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>';
  document.getElementById("panel")!.classList.add("open");
}

function closePanel(): void {
  document.getElementById("panel")!.classList.remove("open");
  document.querySelectorAll<HTMLElement>(".node").forEach((n) => {
    n.classList.remove("active");
  });
}

// ── CSV panel ─────────────────────────────────────────────────────────────────

// ── Snapshot panel ────────────────────────────────────────────────────────────

const SNAPSHOT_COLS = [
  "nombre",
  "experiencia",
  "juegos_este_ano",
  "prioridad",
  "partidas_deseadas",
  "partidas_gm",
] as const;

type SnapCol = (typeof SNAPSHOT_COLS)[number];

const SNAPSHOT_LABELS: Record<SnapCol, string> = {
  nombre: "Nombre",
  experiencia: "Exp.",
  juegos_este_ano: "Juegos",
  prioridad: "Prior.",
  partidas_deseadas: "Desea",
  partidas_gm: "GM",
};

async function openSnapshot(id: number): Promise<void> {
  openPanel(`Snapshot #${id}`);
  const data = (await fetch(`/api/snapshot/${id}`).then((r) =>
    r.json(),
  )) as SnapshotDetail;
  const rows = data.players ?? [];
  const csvTxt = [
    SNAPSHOT_COLS.join(","),
    ...rows.map((r) => SNAPSHOT_COLS.map((c) => String(r[c] ?? "")).join(",")),
  ].join("\n");
  const ck = reg(csvTxt);
  const tbody = rows
    .map(
      (r) =>
        "<tr>" +
        SNAPSHOT_COLS.map((c) => {
          const raw = r[c];
          let v = esc(String(raw ?? ""));
          if (c === "experiencia") {
            const color = raw === "Nuevo" ? "#713f12" : "#166534";
            const bg = raw === "Nuevo" ? "#fef9c3" : "#f0fdf4";
            v = `<span style="font-size:10px;font-weight:700;color:${color};background:${bg};padding:1px 6px;border-radius:4px">${esc(String(raw ?? ""))}</span>`;
          }
          if (c === "prioridad") v = raw === 1 ? "✓" : "";
          return `<td>${v}</td>`;
        }).join("") +
        "</tr>",
    )
    .join("");
  const sourceLabel =
    data.source === "notion_sync"
      ? "☁️ Notion Sync"
      : data.source === "organizar"
        ? "▶ Organizar"
        : "📥 Manual";
  document.getElementById("panel-body")!.innerHTML = `
    <div class="section"><div class="section-title">Snapshot #${id} · ${sourceLabel}</div>
      <div class="node-meta" style="margin-bottom:8px">${esc(data.created_at)}</div>
      <button class="copy-btn" data-ck="${ck}">📋 Copiar tabla CSV</button></div>
    <div class="section"><div class="table-wrap"><table>
      <thead><tr>${SNAPSHOT_COLS.map((c) => `<th>${SNAPSHOT_LABELS[c]}</th>`).join("")}</tr></thead>
      <tbody>${tbody}</tbody>
    </table></div></div>`;
}

// ── Sync panel ────────────────────────────────────────────────────────────────

async function openSyncPanel(id: number): Promise<void> {
  openPanel("Sync Notion");
  const chain = (await fetch("/api/chain").then((r) => r.json())) as ChainData;
  type SyncInfo = { from_id: number; to_id: number; created_at: string };
  const found: { val: SyncInfo | null } = { val: null };
  function findSync(roots: SnapshotNode[]): void {
    for (const root of roots) {
      for (const branch of root.branches ?? []) {
        if (branch.edge.type === "sync" && branch.edge.id === id) {
          found.val = {
            from_id: branch.edge.from_id,
            to_id: branch.edge.to_id,
            created_at: branch.edge.created_at,
          };
        }
        if (branch.output) findSync([branch.output]);
      }
    }
  }
  findSync(chain.roots ?? []);
  const info = found.val;
  if (info !== null) {
    const { from_id, to_id, created_at } = info;
    document.getElementById("panel-body")!.innerHTML = `
      <div class="section">
        <div class="section-title">Detalles del Sync</div>
        <div class="meta-grid">
          <span class="meta-key">Generado</span><span class="meta-val">${esc(created_at)}</span>
          <span class="meta-key">De snapshot</span><span class="meta-val">#${from_id}</span>
          <span class="meta-key">A snapshot</span><span class="meta-val">#${to_id}</span>
        </div>
      </div>`;
  } else {
    document.getElementById("panel-body")!.innerHTML =
      "<p>Sync no encontrado.</p>";
  }
}

// ── Game panel ────────────────────────────────────────────────────────────────

async function openGame(id: number): Promise<void> {
  openPanel(`Partida #${id}`);
  const data = (await fetch(`/api/game/${id}`).then((r) =>
    r.json(),
  )) as GameDetail;
  const mesas = data.mesas ?? [];
  const waiting = data.waiting_list ?? [];
  const copyText = data.copypaste;
  document.getElementById("panel-title")!.textContent = data.created_at;
  let html = "";
  html += `<div class="section"><div class="section-title">Resumen</div><div class="meta-grid">
    <span class="meta-key">Generado</span><span class="meta-val">${esc(data.created_at)}</span>
    <span class="meta-key">Intentos</span><span class="meta-val">${data.intentos}</span>
    <span class="meta-key">Snapshot entrada</span><span class="meta-val">#${data.input_snapshot_id}</span>
    <span class="meta-key">Snapshot salida</span><span class="meta-val">#${data.output_snapshot_id}</span>
  </div></div>`;
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
      const playersTxt = mesa.jugadores.map((j) => j.nombre).join("\n");
      const ckMesa = reg(playersTxt);
      const playerRows = mesa.jugadores
        .map((j, i) => {
          const tag =
            j.etiqueta === "Nuevo"
              ? '<span class="tag tag-nuevo">Nuevo</span>'
              : `<span class="tag tag-antiguo">${esc(j.etiqueta)}</span>`;
          return `<li><span class="p-num">${i + 1}.</span><span class="p-name">${esc(j.nombre)}</span>${tag}</li>`;
        })
        .join("");
      html += `<div class="mesa-card">
        <div class="mesa-header"><span class="mesa-title">Partida ${mesa.numero}</span>${gmTag}</div>
        <ul class="player-list">${playerRows}</ul>
        <button class="copy-btn" data-ck="${ckMesa}" style="margin-top:9px">📋 Copiar jugadores</button>
      </div>`;
    }
    html += "</div>";
  }
  if (waiting.length) {
    const waitTxt = waiting.map((w) => w.nombre).join("\n");
    const ckWait = reg(waitTxt);
    html += `<div class="section"><div class="section-title">Lista de espera</div>
      ${waiting
        .map(
          (w) => `<div class="waiting-item">
        <span class="waiting-name">${esc(w.nombre)}</span>
        <span class="waiting-cupos">${esc(w.cupos)}</span>
      </div>`,
        )
        .join("")}
      <button class="copy-btn" data-ck="${ckWait}">📋 Copiar lista de espera</button>
    </div>`;
  }
  document.getElementById("panel-body")!.innerHTML = html;
}

// ── Run scripts ───────────────────────────────────────────────────────────────

const SCRIPT_LABELS: Record<string, string> = {
  notion_sync: "↻ Sync Notion",
  organizar: "▶ Organizar",
};

async function runScript(
  script: string,
  snapshotId: number | null = null,
): Promise<void> {
  const modal = document.getElementById("modal")!;
  const out = document.getElementById("modal-out")!;
  const titleEl = document.getElementById("modal-title-text")!;
  const iconEl = document.getElementById("modal-icon")!;
  const closeBtn = document.getElementById(
    "btn-modal-close",
  ) as HTMLButtonElement;
  const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
  const btnOrganizar = document.getElementById(
    "btn-organizar",
  ) as HTMLButtonElement;
  out.textContent = "";
  out.className = "modal-out";
  titleEl.textContent = `Ejecutando ${SCRIPT_LABELS[script] ?? script}…`;
  iconEl.innerHTML = '<span class="spinner"></span>';
  closeBtn.disabled = true;
  modal.classList.add("open");
  btnSync.disabled = true;
  btnOrganizar.disabled = true;
  const fetchInit: RequestInit = { method: "POST" };
  if (snapshotId !== null && script === "organizar") {
    fetchInit.headers = { "Content-Type": "application/json" };
    fetchInit.body = JSON.stringify({ snapshot: snapshotId });
  }
  try {
    const res = await fetch(`/api/run/${script}`, fetchInit);
    const data = (await res.json()) as RunResult;
    const ok = data.returncode === 0;
    iconEl.textContent = ok ? "✅" : "❌";
    titleEl.textContent = ok
      ? `${SCRIPT_LABELS[script] ?? script} completado`
      : `Error en ${SCRIPT_LABELS[script] ?? script}`;
    out.textContent =
      (data.stdout ?? "") + (data.stderr ? "\n[stderr]\n" + data.stderr : "");
    if (!ok) out.classList.add("err");
    if (ok) await loadChain();
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

function closeModal(): void {
  document.getElementById("modal")!.classList.remove("open");
}

// ── Button event listeners (no onclick in HTML) ───────────────────────────────

document.getElementById("btn-refresh")!.addEventListener("click", () => {
  void loadChain();
});
document.getElementById("btn-sync")!.addEventListener("click", () => {
  void runScript("notion_sync");
});
document
  .getElementById("btn-organizar")!
  .addEventListener("click", runOrganizar);
document.getElementById("btn-deselect")!.addEventListener("click", deselectCsv);
document
  .getElementById("btn-close-panel")!
  .addEventListener("click", closePanel);
document
  .getElementById("btn-modal-close")!
  .addEventListener("click", closeModal);

void loadChain();
