import type { ChainData, SnapshotNode, GameEdge, SyncEdge } from "./types";
import { updateSelectionUI } from "./selection";

// ── HTML escape ───────────────────────────────────────────────────────────────

export function esc(s: string | null | undefined): string {
  const str = s ?? "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Chain rendering ───────────────────────────────────────────────────────────

export async function loadChain(): Promise<void> {
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
  updateSelectionUI();
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
    <button class="node-delete-btn" data-snapshot-id="${n.id}" title="Eliminar snapshot">🗑</button>
    <div class="node-icon">📋</div><div class="node-label">Snapshot #${n.id}</div>
    <div class="node-name">${esc(n.created_at)}</div>
    <div class="node-meta">${n.player_count} jugadores · ${sourceLabel}</div>${badge}</div>`;
}

function gameNodeHtml(n: GameEdge): string {
  const date = (n.created_at || "").split(" ")[0] ?? "";
  const time = (n.created_at || "").split(" ")[1] ?? "";
  return `<div class="node node-report" data-id="${n.id}" data-type="game">
    <div class="node-icon">📊</div><div class="node-label">Jornada</div>
    <div class="node-name">${esc(date)}</div>
    <div class="node-meta">${esc(time)}<br>${n.mesa_count} partida(s)<br>${n.espera_count} en espera</div></div>`;
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
