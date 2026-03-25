<script lang="ts">
  import { untrack } from "svelte";
  import type { EditPlayerRow, SimilarName, MergePair } from "../types";
  import { createSnapshot, saveSnapshot, fetchNotionPlayers } from "../api";
  import { parsePlayersCsv } from "../utils";
  import { detectSimilarNames } from "../syncUtils";
  import { setActiveNodeId } from "../stores.svelte";
  import SyncResolutionModal from "./SyncResolutionModal.svelte";

  interface Props {
    parentId: number | null;
    initialPlayers: EditPlayerRow[];
    defaultEventType: "manual" | "sync" | "edit";
    autoAction?: 'notion' | 'csv' | null;
    onClose: () => void;
    onChainUpdate: () => void;
    onOpenSnapshot: (id: number) => void;
  }

  let { parentId, initialPlayers, defaultEventType, autoAction = null, onClose, onChainUpdate, onOpenSnapshot }: Props = $props();

  interface DraftPlayer {
    nombre: string;
    experiencia: string;
    juegos_este_ano: number;
    prioridad: number;
    partidas_deseadas: number;
    partidas_gm: number;
  }

  let draftPlayers = $state(untrack(() => initialPlayers.map((p) => ({
    nombre: p.nombre,
    experiencia: p.experiencia ?? "Nuevo",
    juegos_este_ano: p.juegos_este_ano ?? 0,
    prioridad: p.prioridad,
    partidas_deseadas: p.partidas_deseadas,
    partidas_gm: p.partidas_gm,
  }))));
  let eventType = $state(untrack(() => defaultEventType));
  let showCsvModal = $state(false);
  let csvText = $state("");
  let saving = $state(false);
  let isImporting = $state(false);
  let resolutionVisible = $state(false);
  let resolutionPairs = $state<SimilarName[]>([]);
  let fetchedNotionPlayers = $state<any[]>([]);

  // Auto-action on mount
  let autoActionExecuted = $state(false);
  $effect(() => {
    if (!autoActionExecuted && autoAction) {
      autoActionExecuted = true;
      if (autoAction === 'notion') {
        handleImportNotion();
      } else if (autoAction === 'csv') {
        showCsvModal = true;
      }
    }
  });

  function esc(s: string | null | undefined): string {
    const el = document.createElement("span");
    el.textContent = s ?? "";
    return el.innerHTML;
  }

  function handleAddPlayer(): void {
    const nombre = prompt("Nombre del nuevo jugador:");
    if (!nombre) return;
    draftPlayers = [
      ...draftPlayers,
      {
        nombre,
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
    ];
  }

  function handleDeletePlayer(index: number): void {
    draftPlayers = draftPlayers.filter((_, i) => i !== index);
  }

  function handleImportCsv(): void {
    const parsed = parsePlayersCsv(csvText);
    if (parsed.length === 0) {
      alert("No se encontraron jugadores válidos en el CSV");
      return;
    }
    draftPlayers = [...draftPlayers, ...parsed];
    csvText = "";
    showCsvModal = false;
  }

  function handleCancelCsv(): void {
    csvText = "";
    showCsvModal = false;
  }

  async function handleImportNotion(): Promise<void> {
    isImporting = true;
    try {
      const response = await fetchNotionPlayers();
      if (response.error) {
        alert(`Error: ${response.error}`);
        return;
      }

      fetchedNotionPlayers = response.players;

      // Detect similar names between Notion and current draft
      const notionNames = response.players.map((p: any) => p.nombre);
      const draftNames = draftPlayers.map((p) => p.nombre);
      const similar = detectSimilarNames(notionNames, draftNames, 0.75);

      if (similar.length > 0) {
        // Show resolution modal
        resolutionPairs = similar;
        resolutionVisible = true;
      } else {
        // No conflicts, merge directly
        mergeNotionPlayers([]);
      }
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    } finally {
      isImporting = false;
    }
  }

  function mergeNotionPlayers(merges: MergePair[]): void {
    const mergeMap = new Map(merges.map((m) => [m.from, m.to]));

    // Update existing players with Notion data
    const updatedPlayers = draftPlayers.map((player) => {
      const notionName = mergeMap.get(player.nombre) || player.nombre;
      const notionPlayer = fetchedNotionPlayers.find(
        (p: any) => p.nombre === notionName
      );
      if (notionPlayer) {
        return {
          ...player,
          nombre: notionName,
          experiencia: notionPlayer.experiencia,
          juegos_este_ano: notionPlayer.juegos_este_ano,
        };
      }
      return player;
    });

    // Strict Roster Rule: Only add new players if creating from scratch (parentId === null)
    if (parentId === null) {
      const existingNames = new Set(updatedPlayers.map((p) => p.nombre));
      const newPlayers = fetchedNotionPlayers
        .filter((p: any) => !existingNames.has(p.nombre))
        .map((p: any) => ({
          nombre: p.nombre,
          experiencia: p.experiencia,
          juegos_este_ano: p.juegos_este_ano,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
        }));

      draftPlayers = [...updatedPlayers, ...newPlayers];
    } else {
      // When updating existing list, only update existing players
      draftPlayers = updatedPlayers;
    }

    eventType = "sync";
    resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
  }

  function handleResolutionComplete(merges: MergePair[]): void {
    mergeNotionPlayers(merges);
  }

  function handleResolutionCancel(): void {
    resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
  }

  async function handleSave(): Promise<void> {
    if (draftPlayers.length === 0) {
      alert("Agrega al menos un jugador antes de guardar");
      return;
    }

    saving = true;
    try {
      const players: EditPlayerRow[] = draftPlayers.map((p) => ({
        nombre: p.nombre,
        experiencia: p.experiencia,
        juegos_este_ano: p.juegos_este_ano,
        prioridad: p.prioridad,
        partidas_deseadas: p.partidas_deseadas,
        partidas_gm: p.partidas_gm,
      }));

      const result = await saveSnapshot({
        parent_id: parentId,
        event_type: eventType,
        players,
      });

      if (result.error) {
        alert(`Error: ${result.error}`);
        return;
      }

      onClose();
      onChainUpdate();
      if (result.snapshot_id !== undefined) {
        setActiveNodeId(String(result.snapshot_id));
        onOpenSnapshot(result.snapshot_id);
      }
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    } finally {
      saving = false;
    }
  }

  function handleCheckboxChange(e: Event, index: number, field: "prioridad" | "partidas_gm"): void {
    const cb = e.target as HTMLInputElement;
    const updated = [...draftPlayers];
    updated[index]![field] = cb.checked ? 1 : 0;
    draftPlayers = updated;
  }

  function handleNumberChange(e: Event, index: number, field: "juegos_este_ano" | "partidas_deseadas"): void {
    const input = e.target as HTMLInputElement;
    const updated = [...draftPlayers];
    updated[index]![field] = parseInt(input.value, 10) || 0;
    draftPlayers = updated;
  }

  function autofocus(node: HTMLTextAreaElement) {
    node.focus();
  }
</script>

<div class="panel-body-fixed">
  <div class="section" style="margin-bottom: 16px;">
    <div class="section-title">Nueva Versión</div>
    <div class="node-meta" style="margin-bottom: 8px;">
      Crea una nueva versión desde cero o importa jugadores desde CSV
    </div>
    <div style="display: flex; gap: 8px;">
      <button class="btn btn-secondary" onclick={handleAddPlayer}>
        ➕ Agregar jugador
      </button>
      {#if parentId === null}
        <button class="btn btn-secondary" onclick={() => (showCsvModal = true)}>
          📥 Pegar CSV
        </button>
        <button
          class="btn btn-secondary"
          onclick={handleImportNotion}
          disabled={isImporting}
        >
          {isImporting ? "⏳ Importando..." : "☁️ Importar de Notion"}
        </button>
      {/if}
    </div>
  </div>
  <div class="section-title" style="margin-bottom: 6px;">
    Jugadores ({draftPlayers.length})
  </div>
</div>

{#if draftPlayers.length > 0}
  <div class="table-wrap flex-table-wrap">
    <table>
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Exp.</th>
          <th>Juegos</th>
          <th>Prior.</th>
          <th>Desea</th>
          <th>GM</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each draftPlayers as player, i (i)}
          {@const expColor =
            player.experiencia === "Nuevo" ? "#713f12" : "#166534"}
          {@const expBg =
            player.experiencia === "Nuevo" ? "#fef9c3" : "#f0fdf4"}
          <tr>
            <td><input type="text" class="player-name-input" bind:value={player.nombre} placeholder="Nombre del jugador" /></td>
            <td>
              <span
                style="font-size:10px;font-weight:700;color:{expColor};background:{expBg};padding:1px 6px;border-radius:4px"
              >
                {esc(player.experiencia)}
              </span>
            </td>
            <td>
              <input
                type="number"
                value={player.juegos_este_ano}
                min="0"
                style="width: 38px;"
                onchange={(e) => handleNumberChange(e, i, "juegos_este_ano")}
              />
            </td>
            <td>
              <input
                type="checkbox"
                checked={player.prioridad === 1}
                onchange={(e) => handleCheckboxChange(e, i, "prioridad")}
              />
            </td>
            <td>
              <input
                type="number"
                value={player.partidas_deseadas}
                min="1"
                max="9"
                style="width: 38px;"
                onchange={(e) => handleNumberChange(e, i, "partidas_deseadas")}
              />
            </td>
            <td>
              <input
                type="checkbox"
                checked={player.partidas_gm > 0}
                onchange={(e) => handleCheckboxChange(e, i, "partidas_gm")}
              />
            </td>
            <td>
              <button
                class="btn-ghost btn-delete"
                title="Eliminar"
                onclick={() => handleDeletePlayer(i)}
              >
                🗑
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else}
  <div class="empty-draft">
    <p>No hay jugadores en el borrador.</p>
    <p>Agrega jugadores manualmente o importa desde CSV.</p>
  </div>
{/if}

<div class="panel-footer">
  <button
    class="btn btn-primary"
    style="width: 100%;"
    onclick={handleSave}
    disabled={saving || draftPlayers.length === 0}
    title={draftPlayers.length === 0 ? "Agrega al menos un jugador para guardar" : ""}
  >
    {saving ? "Guardando..." : (eventType === 'sync' ? '✨ Guardar Sincronización' : (parentId ? '✨ Guardar Edición' : '✨ Guardar Nueva Lista'))}
  </button>
</div>

{#if showCsvModal}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="modal-overlay" onclick={handleCancelCsv}>
    <div class="modal-content" onclick={(e) => e.stopPropagation()}>
      <div class="modal-title">Pegar CSV</div>
      <p class="modal-description">
        Pega el contenido CSV con las columnas: nombre, experiencia,
        juegos_este_ano, prioridad, partidas_deseadas, partidas_gm
      </p>
      <textarea
        use:autofocus
        bind:value={csvText}
        placeholder="nombre,experiencia,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm&#10;Alice,Nuevo,0,0,1,0&#10;Bob,Antiguo,3,1,2,1"
        rows="10"
      ></textarea>
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick={handleCancelCsv}>
          Cancelar
        </button>
        <button class="btn btn-primary" onclick={handleImportCsv}>
          Importar
        </button>
      </div>
    </div>
  </div>
{/if}

<SyncResolutionModal
  visible={resolutionVisible}
  pairs={resolutionPairs}
  onComplete={handleResolutionComplete}
  onCancel={handleResolutionCancel}
/>

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

  .player-name-input {
    border: none;
    background: transparent;
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    width: 100%;
    padding: 2px 4px;
    border-radius: 4px;
    transition: border-color 0.15s;
  }

  .player-name-input:focus {
    outline: none;
    border: 1px solid var(--accent);
    background: var(--surface);
  }

  .btn-delete {
    font-size: 12px;
    padding: 2px 6px;
    opacity: 0.7;
    transition: opacity 0.15s;
  }

  .btn-delete:hover {
    opacity: 1;
  }

  .empty-draft {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 40px;
    color: var(--muted);
    text-align: center;
  }

  .empty-draft p {
    font-size: 13px;
    margin: 0;
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .modal-content {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    width: 90%;
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
  }

  .modal-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .modal-description {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 16px;
  }

  .modal-content textarea {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-family: monospace;
    font-size: 12px;
    background: var(--surface2);
    color: var(--text);
    resize: vertical;
    margin-bottom: 16px;
  }

  .modal-content textarea:focus {
    outline: 2px solid var(--accent);
    border-color: transparent;
  }

  .modal-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
</style>