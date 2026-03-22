import type {
  ChainData,
  SnapshotNode,
  SnapshotDetail,
  GameDetail,
  DeleteResult,
  EditPlayerRow,
  EditSnapshotResponse,
} from "./types";
import { esc, loadChain } from "./chain";
import { reg } from "./clipboard";
import {
  getSelectedSnapshot,
  setSelectedSnapshot,
  deselectSnapshot,
} from "./selection";

// ── Panel management ──────────────────────────────────────────────────────────

export function openPanel(title: string): void {
  document.getElementById("panel-title")!.textContent = title;
  document.getElementById("panel-body")!.innerHTML =
    '<p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>';
  document.getElementById("panel")!.classList.add("open");
}

export function closePanel(): void {
  document.getElementById("panel")!.classList.remove("open");
  document.querySelectorAll<HTMLElement>(".node").forEach((n) => {
    n.classList.remove("active");
  });
}

// Dim rows excluded from the next jornada via the player-keep checkbox.
document
  .getElementById("panel-body")!
  .addEventListener("change", (e: Event) => {
    const cb = (e.target as Element).closest<HTMLInputElement>(".player-keep");
    if (!cb) return;
    const tr = cb.closest("tr");
    if (tr) tr.classList.toggle("excluded", !cb.checked);
  });

// ── Snapshot panel ────────────────────────────────────────────────────────────

export async function openSnapshot(id: number): Promise<void> {
  openPanel(`Snapshot #${id}`);
  const data = (await fetch(`/api/snapshot/${id}`).then((r) =>
    r.json(),
  )) as SnapshotDetail;
  const rows = data.players ?? [];
  const CSV_COLS = [
    "nombre",
    "experiencia",
    "juegos_este_ano",
    "prioridad",
    "partidas_deseadas",
    "partidas_gm",
  ] as const;
  type Col = (typeof CSV_COLS)[number];
  const csvTxt = [
    CSV_COLS.join(","),
    ...rows.map((r) =>
      CSV_COLS.map((c: Col) =>
        String((r as Record<Col, string | number>)[c]),
      ).join(","),
    ),
  ].join("\n");
  const ck = reg(csvTxt);
  const sourceLabel =
    data.source === "notion_sync"
      ? "☁️ Notion Sync"
      : data.source === "organizar"
        ? "▶ Organizar"
        : "📥 Manual";

  const editRows = rows
    .map((r) => {
      const checked = (r["prioridad"] as number) === 1 ? "checked" : "";
      const gmChecked = (r["partidas_gm"] as number) > 0 ? "checked" : "";
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
    })
    .join("");

  document.getElementById("panel-body")!.innerHTML = `
    <div class="section"><div class="section-title">Snapshot #${id} · ${sourceLabel}</div>
      <div class="node-meta" style="margin-bottom:8px">${esc(data.created_at)}</div>
      <button class="copy-btn" data-ck="${ck}">📋 Copiar tabla CSV</button></div>
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

  document.getElementById("btn-apply-edit")!.addEventListener("click", () => {
    void applySnapshotEdit(id);
  });
}

async function applySnapshotEdit(sourceId: number): Promise<void> {
  const table = document.getElementById("snapshot-edit-table");
  if (!table) return;
  const players: EditPlayerRow[] = [];
  table.querySelectorAll<HTMLTableRowElement>("tbody tr").forEach((tr) => {
    const keep = tr.querySelector<HTMLInputElement>(".player-keep");
    if (!keep?.checked) return;
    const nombre = tr.dataset["nombre"] ?? "";
    const prio = tr.querySelector<HTMLInputElement>(".player-prio");
    const deseadas = tr.querySelector<HTMLInputElement>(".player-deseadas");
    const gm = tr.querySelector<HTMLInputElement>(".player-gm");
    players.push({
      nombre,
      prioridad: prio?.checked ? 1 : 0,
      partidas_deseadas: parseInt(deseadas?.value ?? "1", 10),
      partidas_gm: gm?.checked ? 1 : 0,
    });
  });
  const btn = document.getElementById("btn-apply-edit") as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = "Creando…";
  try {
    const res = await fetch(`/api/snapshot/${sourceId}/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ players }),
    });
    const data = (await res.json()) as EditSnapshotResponse;
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
      void openSnapshot(newId);
    }
  } catch (e) {
    alert(`Error de conexión: ${String(e)}`);
    btn.disabled = false;
    btn.textContent = "✨ Crear snapshot manual con estos ajustes";
  }
}

// ── Sync panel ────────────────────────────────────────────────────────────────

export async function openSyncPanel(id: number): Promise<void> {
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

export async function openGame(id: number): Promise<void> {
  openPanel(`Jornada #${id}`);
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

// ── Delete snapshot ───────────────────────────────────────────────────────────

export async function deleteSnapshot(id: number): Promise<void> {
  if (
    !confirm(
      `¿Eliminar snapshot #${id} y todos sus descendientes?\nEsta acción no se puede deshacer.`,
    )
  )
    return;
  try {
    const res = await fetch(`/api/snapshot/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const err = (await res.json()) as DeleteResult;
      alert(`Error al eliminar: ${err.error ?? res.status}`);
      return;
    }
    const data = (await res.json()) as DeleteResult;
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
