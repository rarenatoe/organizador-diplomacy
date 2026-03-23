<script lang="ts">
  import type { SnapshotDetail, EditPlayerRow } from "../types";
  import { fetchSnapshot, editSnapshot, addPlayer, renamePlayer } from "../api";
  import { setSelectedSnapshot } from "../stores.svelte";

  interface Props {
    id: number;
    onclose: () => void;
    onchainUpdate: () => void;
    onopenSnapshot: (id: number) => void;
  }

  let { id, onclose, onchainUpdate, onopenSnapshot }: Props = $props();

  let data = $state<SnapshotDetail | null>(null);
  let loading = $state(true);

  const CSV_COLS = [
    "nombre",
    "experiencia",
    "juegos_este_ano",
    "prioridad",
    "partidas_deseadas",
    "partidas_gm",
  ] as const;

  type Col = (typeof CSV_COLS)[number];

  function esc(s: string | null | undefined): string {
    const el = document.createElement("span");
    el.textContent = s ?? "";
    return el.innerHTML;
  }

  function sourceLabel(source: string | undefined): string {
    if (source === "notion_sync") return "☁️ Notion Sync";
    if (source === "organizar") return "▶ Organizar";
    return "📥 Manual";
  }

  async function loadSnapshot(): Promise<void> {
    loading = true;
    try {
      data = await fetchSnapshot(id);
    } finally {
      loading = false;
    }
  }

  function getCsvText(): string {
    if (!data?.players) return "";
    const rows = data.players;
    return [
      CSV_COLS.join(","),
      ...rows.map((r) =>
        CSV_COLS.map((c: Col) =>
          String((r as Record<Col, string | number>)[c]),
        ).join(","),
      ),
    ].join("\n");
  }

  async function copyCsv(): Promise<void> {
    await navigator.clipboard.writeText(getCsvText());
  }

  async function handleApplyEdit(): Promise<void> {
    const table = document.getElementById("snapshot-edit-table");
    if (!table || !data) return;
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
    const result = await editSnapshot(id, players);
    if (result.error) {
      alert(`Error: ${result.error}`);
      return;
    }
    onclose();
    onchainUpdate();
    if (result.snapshot_id !== undefined) {
      setSelectedSnapshot(result.snapshot_id);
      onopenSnapshot(result.snapshot_id);
    }
  }

  async function handleRename(oldName: string): Promise<void> {
    const newName = prompt(`Renombrar jugador "${oldName}" a:`, oldName);
    if (!newName || newName === oldName) return;
    const result = await renamePlayer(oldName, newName);
    if (result.error) {
      alert(`Error: ${result.error}`);
      return;
    }
    await loadSnapshot();
    onchainUpdate();
  }

  async function handleAddPlayer(): Promise<void> {
    const nombre = prompt("Nombre del nuevo jugador:");
    if (!nombre) return;
    const experiencia = prompt("Experiencia (Nuevo/Antiguo):", "Nuevo");
    if (!experiencia) return;
    const juegosStr = prompt("Juegos este año:", "0");
    const juegos = parseInt(juegosStr ?? "0", 10);
    const result = await addPlayer(id, {
      nombre,
      experiencia,
      juegos_este_ano: juegos,
      prioridad: 0,
      partidas_deseadas: 1,
      partidas_gm: 0,
    });
    if (result.error) {
      alert(`Error: ${result.error}`);
      return;
    }
    await loadSnapshot();
    onchainUpdate();
  }

  function handleCheckboxChange(e: Event): void {
    const cb = (e.target as Element).closest<HTMLInputElement>(".player-keep");
    if (!cb) return;
    const tr = cb.closest("tr");
    if (tr) tr.classList.toggle("excluded", !cb.checked);
  }

  $effect(() => {
    void loadSnapshot();
  });
</script>

{#if loading}
  <p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>
{:else if data}
  {@const rows = data.players ?? []}
  <div class="panel-body-fixed">
    <div class="section" style="margin-bottom: 16px;">
      <div class="section-title">Snapshot #{id} · {sourceLabel(data.source)}</div>
      <div class="node-meta" style="margin-bottom:8px">{esc(data.created_at)}</div>
      <button class="copy-btn" onclick={copyCsv}>📋 Copiar tabla CSV</button>
    </div>
    <div class="section-title" style="margin-bottom:6px">
      Jugadores <span
        style="color:var(--muted);font-weight:400;text-transform:none;font-size:11px"
        >— desactiva para excluir de la siguiente jornada</span
      >
    </div>
  </div>

  <div class="table-wrap flex-table-wrap">
    <table id="snapshot-edit-table">
          <thead>
            <tr>
              <th></th>
              <th>Nombre</th>
              <th></th>
              <th>Exp.</th>
              <th>Juegos</th>
              <th>Prior.</th>
              <th>Desea</th>
              <th>GM</th>
            </tr>
          </thead>
          <tbody onchange={handleCheckboxChange}>
            {#each rows as r}
              {@const nombre = esc(String(r["nombre"] ?? ""))}
              {@const expColor =
                r["experiencia"] === "Nuevo" ? "#713f12" : "#166534"}
              {@const expBg =
                r["experiencia"] === "Nuevo" ? "#fef9c3" : "#f0fdf4"}
              <tr data-nombre={nombre}>
                <td
                  ><input
                    type="checkbox"
                    class="player-keep"
                    checked
                    title="Incluir"
                  /></td
                >
                <td><span class="player-name">{nombre}</span></td>
                <td style="padding-left: 0; width: 32px;">
                  <button
                    class="btn-ghost btn-rename"
                    title="Renombrar"
                    onclick={() => handleRename(String(r["nombre"] ?? ""))}
                    >✏️</button
                  >
                </td>
                <td
                  ><span
                    style="font-size:10px;font-weight:700;color:{expColor};background:{expBg};padding:1px 6px;border-radius:4px"
                    >{esc(String(r["experiencia"] ?? ""))}</span
                  ></td
                >
                <td>{String(r["juegos_este_ano"] ?? "")}</td>
                <td
                  ><input
                    type="checkbox"
                    class="player-prio"
                    checked={r["prioridad"] === 1}
                  /></td
                >
                <td
                  ><input
                    type="number"
                    class="player-deseadas"
                    value={String(r["partidas_deseadas"] ?? "1")}
                    min="1"
                    max="9"
                    style="width:38px"
                  /></td
                >
                <td
                  ><input
                    type="checkbox"
                    class="player-gm"
                    checked={(r["partidas_gm"] as number) > 0}
                  /></td
                >
              </tr>
            {/each}
          </tbody>
        </table>
  </div>
  <div class="panel-footer">
    <button
      class="btn btn-secondary"
      style="width:100%"
      onclick={handleAddPlayer}>➕ Agregar jugador</button
    >
    <button class="btn btn-primary" style="width:100%" onclick={handleApplyEdit}
      >✨ Crear snapshot manual con estos ajustes</button
    >
  </div>
{/if}

<style>
  .section {
    margin-bottom: 22px;
  }

  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--muted);
    margin-bottom: 10px;
  }

  .copy-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 14px;
    width: 100%;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text);
    transition: background 0.15s;
  }

  .copy-btn:hover {
    background: var(--border);
  }

  :global(.copy-btn.ok) {
    background: var(--success);
    color: #fff;
    border-color: var(--success);
  }

  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    min-width: max-content;
  }

  th {
    background: var(--surface2);
    padding: 7px 9px;
    text-align: left;
    font-weight: 600;
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }

  td {
    padding: 6px 9px;
    border-bottom: 1px solid var(--border);
  }

  tr:last-child td {
    border-bottom: none;
  }

  tr:hover td {
    background: var(--surface2);
  }

  .flex-table-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
    margin: 0 18px 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    overscroll-behavior-y: none;
  }

  .flex-table-wrap th {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--surface2);
    transform: translateZ(0);
    background-clip: padding-box;
    border-bottom: 1px solid var(--border);
    box-shadow: none;
  }

  .flex-table-wrap th:nth-child(1),
  .flex-table-wrap td:nth-child(1) {
    width: 32px;
    min-width: 32px;
    padding: 6px 9px;
    position: sticky;
    left: 0;
    background: var(--surface);
    z-index: 5;
  }

  .flex-table-wrap th:nth-child(2),
  .flex-table-wrap td:nth-child(2) {
    position: sticky;
    left: 32px;
    background: var(--surface);
    z-index: 5;
    box-shadow: 2px 0 4px -2px rgba(0, 0, 0, 0.1);
  }

  .flex-table-wrap tbody tr:hover td:nth-child(1),
  .flex-table-wrap tbody tr:hover td:nth-child(2) {
    background: var(--surface2);
  }

  .flex-table-wrap th:nth-child(1) {
    z-index: 12;
    background: var(--surface2);
  }

  .flex-table-wrap th:nth-child(2) {
    z-index: 12;
    background: var(--surface2);
    box-shadow: 2px 0 4px -2px rgba(0, 0, 0, 0.1);
  }

  .flex-table-wrap input[type="checkbox"] {
    width: 14px;
    height: 14px;
    cursor: pointer;
    accent-color: var(--accent);
  }

  .flex-table-wrap input[type="number"] {
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 12px;
    background: var(--surface);
    color: var(--text);
  }

  .flex-table-wrap input[type="number"]:focus {
    outline: 2px solid var(--accent);
    border-color: transparent;
  }

  tbody :global(tr.excluded) {
    opacity: 0.35;
  }

  .player-name {
    white-space: nowrap;
  }

  .btn-rename {
    flex-shrink: 0;
    font-size: 12px;
    padding: 2px 6px;
    opacity: 0.7;
    transition: opacity 0.15s;
  }

  .btn-rename:hover {
    opacity: 1;
  }
</style>
