<script lang="ts">
  import { onMount, tick, untrack } from "svelte";
  import type {
    EditPlayerRow,
    SimilarName,
    MergePair,
    NotionPlayer,
  } from "../../types";
  import {
    saveSnapshot,
    fetchNotionPlayers,
    lookupPlayerHistory,
    getAllPlayers,
    checkPlayerSimilarity,
  } from "../../api";
  import { parsePlayersCsv, normalizeName } from "../../utils";
  import { setActiveNodeId } from "../../stores.svelte";
  import { clickOutside } from "../../clickOutside";
  import SyncResolutionModal from "../modals/SyncResolutionModal.svelte";
  import CsvImportModal from "../modals/CsvImportModal.svelte";
  import Button from "../ui/Button.svelte";
  import PanelLayout from "../layout/PanelLayout.svelte";
  import Badge from "../ui/Badge.svelte";
  import Tooltip from "../ui/Tooltip.svelte";
  import DataTable, { type ColumnDef } from "../layout/DataTable.svelte";

  interface Props {
    parentId: number | null;
    initialPlayers: EditPlayerRow[];
    defaultEventType: "manual" | "sync" | "edit";
    autoAction?: "notion" | "csv" | null;
    onClose: () => void;
    onCancel: () => void;
    onChainUpdate: () => void;
    onOpenSnapshot: (id: number) => void;
    onShowError: (title: string, output: string) => void;
  }

  let {
    parentId,
    initialPlayers,
    defaultEventType,
    autoAction = null,
    onClose,
    onCancel,
    onChainUpdate,
    onOpenSnapshot,
    onShowError,
  }: Props = $props();

  let draftPlayers = $state(
    untrack(() =>
      initialPlayers.map((p) => ({
        nombre: p.nombre,
        original_nombre: p.nombre, // Track original name for rename detection
        experiencia: p.experiencia ?? "Nuevo",
        juegos_este_ano: p.juegos_este_ano ?? 0,
        prioridad: p.prioridad,
        partidas_deseadas: p.partidas_deseadas,
        partidas_gm: p.partidas_gm,
        historyRestored: false, // Default for existing players
      })),
    ),
  );
  let eventType = $state(untrack(() => defaultEventType));
  let knownPlayers: string[] = $state([]);
  let isAddingPlayer = $state(false);
  let newPlayerSearchQuery = $state("");
  let pendingCsvPlayers: any[] = $state([]);
  let showCsvModal = $state(false);
  let saving = $state(false);
  let isImporting = $state(false);
  let resolutionVisible = $state(false);
  let resolutionPairs = $state<SimilarName[]>([]);
  let fetchedNotionPlayers = $state<NotionPlayer[]>([]);

  // Auto-action on mount
  let autoActionExecuted = $state(false);
  $effect(() => {
    if (!autoActionExecuted && autoAction) {
      autoActionExecuted = true;
      if (autoAction === "notion") {
        handleImportNotion();
      } else if (autoAction === "csv") {
        showCsvModal = true;
      }
    }
  });

  onMount(() => {
    getAllPlayers()
      .then((res) => {
        knownPlayers = res.names;
      })
      .catch(console.error);
  });

  async function handleAddPlayer(): Promise<void> {
    isAddingPlayer = true;
    newPlayerSearchQuery = "";
    await tick();
    const tableContainer = document.querySelector(".table-container");
    if (tableContainer) tableContainer.scrollTop = tableContainer.scrollHeight;
  }

  function focusOnMount(node: HTMLInputElement) {
    node.focus();
  }

  async function confirmAddPlayer(nombre: string): Promise<void> {
    if (!nombre.trim()) {
      isAddingPlayer = false;
      return;
    }

    let historyRestored = false;
    let experiencia = "Nuevo";
    let juegos_este_ano = 0;
    let prioridad = 0;
    let partidas_deseadas = 1;
    let partidas_gm = 0;

    try {
      const response = await lookupPlayerHistory(
        [nombre],
        parentId || undefined,
      );
      const playerData = response.players[nombre];
      if (playerData) {
        experiencia = playerData.experiencia;
        juegos_este_ano = playerData.juegos_este_ano;
        prioridad = playerData.prioridad;
        partidas_deseadas = playerData.partidas_deseadas;
        partidas_gm = playerData.partidas_gm;
        historyRestored = playerData.source === "history";
      }
    } catch (e) {
      console.warn("Failed to lookup player history:", e);
    }

    draftPlayers = [
      ...draftPlayers,
      {
        nombre,
        original_nombre: nombre,
        experiencia,
        juegos_este_ano,
        prioridad,
        partidas_deseadas,
        partidas_gm,
        historyRestored,
      },
    ];
    isAddingPlayer = false;
    newPlayerSearchQuery = "";
  }

  function handleDeletePlayer(index: number): void {
    draftPlayers = draftPlayers.filter((_, i) => i !== index);
  }

  async function handleImportCsv(text: string): Promise<void> {
    const parsed = parsePlayersCsv(text);
    if (parsed.length === 0) {
      onShowError(
        "CSV Inválido",
        "No se encontraron jugadores válidos en el archivo.",
      );
      return;
    }

    showCsvModal = false;
    const playerNames = parsed.map((p) => p.nombre);

    try {
      const checkRes = await checkPlayerSimilarity(playerNames);
      if (checkRes.similarities && checkRes.similarities.length > 0) {
        pendingCsvPlayers = parsed;
        resolutionPairs = checkRes.similarities;
        resolutionVisible = true;
        return;
      }
    } catch (e) {
      console.error("Similarity check failed", e);
    }

    await applyFinalCsvPlayers(parsed);
  }

  async function applyFinalCsvPlayers(parsedRows: any[]) {
    const playerNames = parsedRows.map((p) => p.nombre);
    let enhancedPlayers = parsedRows.map((p) => ({
      ...p,
      original_nombre: p.nombre,
      historyRestored: false,
    }));

    try {
      const response = await lookupPlayerHistory(
        playerNames,
        parentId || undefined,
      );
      enhancedPlayers = parsedRows.map((p) => {
        const playerData = response.players[p.nombre];
        if (playerData) {
          return {
            ...p,
            original_nombre: p.nombre,
            experiencia: playerData.experiencia,
            juegos_este_ano: playerData.juegos_este_ano,
            prioridad: playerData.prioridad,
            partidas_deseadas: playerData.partidas_deseadas,
            partidas_gm: playerData.partidas_gm,
            historyRestored: playerData.source === "history",
          };
        }
        return {
          ...p,
          original_nombre: p.nombre,
          partidas_deseadas: 1,
          partidas_gm: 0,
          historyRestored: false,
        };
      });
    } catch (e) {
      console.warn("Failed to lookup player history for CSV import:", e);
    }

    draftPlayers = [...draftPlayers, ...enhancedPlayers];
  }

  function handleCancelCsv(): void {
    showCsvModal = false;
  }

  async function handleImportNotion(): Promise<void> {
    isImporting = true;
    try {
      const draftNames = draftPlayers.map((p) => p.nombre);
      const response = await fetchNotionPlayers(draftNames);

      if (response.error) {
        onShowError("Aviso / Error", `Error: ${response.error}`);
        return;
      }

      fetchedNotionPlayers = response.players;

      if (response.similar_names && response.similar_names.length > 0) {
        // Show resolution modal
        resolutionPairs = response.similar_names;
        resolutionVisible = true;
      } else {
        // No conflicts, merge directly
        mergeNotionPlayers([]);
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
    } finally {
      isImporting = false;
    }
  }

  function mergeNotionPlayers(merges: MergePair[]): void {
    const mergeMap = new Map(merges.map((m) => [m.from, m]));

    // Update existing players with Notion data
    const updatedPlayers = draftPlayers.map((player) => {
      const mergeInfo = mergeMap.get(player.nombre);
      const notionName = mergeInfo ? mergeInfo.to : player.nombre;
      const normName = normalizeName(notionName);

      const notionPlayer = fetchedNotionPlayers.find(
        (p) =>
          normalizeName(p.nombre) === normName ||
          p.alias?.some((a) => normalizeName(a) === normName),
      );

      if (notionPlayer) {
        return {
          ...player,
          nombre:
            mergeInfo?.action === "merge_notion"
              ? notionPlayer.nombre
              : player.nombre,
          experiencia: notionPlayer.experiencia,
          juegos_este_ano: notionPlayer.juegos_este_ano,
        };
      }
      return player;
    });

    // Strict Roster Rule: Only add new players if creating from scratch (parentId === null)
    if (parentId === null) {
      const existingNames = new Set(
        updatedPlayers.map((p) => normalizeName(p.nombre)),
      );
      const newPlayers = fetchedNotionPlayers
        .filter((p) => !existingNames.has(normalizeName(p.nombre)))
        .map((p) => ({
          nombre: p.nombre,
          original_nombre: p.nombre,
          experiencia: p.experiencia,
          juegos_este_ano: p.juegos_este_ano,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
          historyRestored: false, // Notion sync doesn't use history restoration
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

  async function handleResolutionComplete(merges: MergePair[]): Promise<void> {
    const resolvedMerges = merges;
    resolutionVisible = false;

    if (pendingCsvPlayers.length > 0) {
      // It's a CSV import resolution
      const resolvedRows = pendingCsvPlayers.map((row) => {
        const mergeTarget = resolvedMerges[row.nombre];
        if (mergeTarget) {
          return { ...row, nombre: mergeTarget.to };
        }
        return row;
      });
      pendingCsvPlayers = [];
      await applyFinalCsvPlayers(resolvedRows);
    } else {
      // It's a Notion Sync resolution (existing logic)
      await handleImportNotion();
    }
  }

  function handleResolutionCancel(): void {
    resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
  }

  async function handleSave(): Promise<void> {
    if (draftPlayers.length === 0) {
      onShowError(
        "Aviso / Error",
        "Agrega al menos un jugador antes de guardar",
      );
      return;
    }

    saving = true;
    try {
      // Calculate manual renames by comparing current name to original
      const manualRenames = draftPlayers
        .filter((p) => p.original_nombre && p.original_nombre !== p.nombre)
        .map((p) => ({ from: p.original_nombre, to: p.nombre }));

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
        renames: manualRenames,
      });

      if (result.error) {
        onShowError("Aviso / Error", `Error: ${result.error}`);
        return;
      }

      onClose();
      onChainUpdate();
      if (result.snapshot_id !== undefined) {
        setActiveNodeId(result.snapshot_id as number);
        onOpenSnapshot(result.snapshot_id);
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
    } finally {
      saving = false;
    }
  }

  function handleCheckboxChange(
    e: Event,
    index: number,
    field: "prioridad" | "partidas_gm",
  ): void {
    const cb = e.target as HTMLInputElement;
    const updated = [...draftPlayers];
    updated[index]![field] = cb.checked ? 1 : 0;
    draftPlayers = updated;
  }

  function handleNumberChange(
    e: Event,
    index: number,
    field: "juegos_este_ano" | "partidas_deseadas",
  ): void {
    const input = e.target as HTMLInputElement;
    const updated = [...draftPlayers];
    updated[index]![field] = parseInt(input.value, 10) || 0;
    draftPlayers = updated;
  }
</script>

<PanelLayout scrollable={false}>
  {#snippet header()}
    <div class="section" style="margin-bottom: 16px;">
      <div class="section-title">Nueva Versión</div>
      <div class="node-meta" style="margin-bottom: 8px;">
        Crea una nueva versión desde cero o importa jugadores desde CSV
      </div>
      <div style="display: flex; gap: 8px;">
        <Button variant="secondary" onclick={handleAddPlayer}>
          ➕ Agregar jugador
        </Button>
        {#if parentId === null}
          <Button variant="secondary" onclick={() => (showCsvModal = true)}>
            📥 Pegar CSV
          </Button>
          <Button
            variant="secondary"
            onclick={handleImportNotion}
            disabled={isImporting}
          >
            {isImporting ? "⏳ Sincronizando..." : "🔗 Importar Notion"}
          </Button>
        {/if}
      </div>
    </div>
    <div class="section-title" style="margin-bottom: 6px;">
      Jugadores ({draftPlayers.length})
    </div>
  {/snippet}

  {#snippet body()}
    {#if draftPlayers.length > 0}
      {#snippet nameInput(row: EditPlayerRow, i: number)}
        <div style="display: flex; align-items: center; gap: 4px;">
          <input
            type="text"
            class="table-input table-input-ghost text-strong"
            bind:value={row.nombre}
            placeholder="Nombre del jugador"
          />
          {#if row.historyRestored}
            <Tooltip
              text="Perfil histórico cargado desde la base de datos"
              icon="📚"
            />
          {/if}
        </div>
      {/snippet}

      {#snippet expCell(row: EditPlayerRow)}
        {#if row.experiencia}
          <Badge
            variant={row.experiencia === "Nuevo" ? "warning" : "success"}
            text={row.experiencia}
            fixedWidth={true}
          />
        {/if}
      {/snippet}

      {#snippet gamesInput(row: EditPlayerRow, i: number)}
        <input
          type="number"
          class="table-input"
          value={row.juegos_este_ano}
          min="0"
          style="width: 48px;"
          onchange={(e) => handleNumberChange(e, i, "juegos_este_ano")}
        />
      {/snippet}

      {#snippet priorInput(row: EditPlayerRow, i: number)}
        <input
          type="checkbox"
          class="table-checkbox"
          checked={row.prioridad === 1}
          onchange={(e) => handleCheckboxChange(e, i, "prioridad")}
        />
      {/snippet}

      {#snippet deseaInput(row: EditPlayerRow, i: number)}
        <input
          type="number"
          class="table-input"
          value={row.partidas_deseadas}
          min="1"
          max="9"
          style="width: 48px;"
          onchange={(e) => handleNumberChange(e, i, "partidas_deseadas")}
        />
      {/snippet}

      {#snippet gmInput(row: EditPlayerRow, i: number)}
        <input
          type="checkbox"
          class="table-checkbox"
          checked={row.partidas_gm > 0}
          onchange={(e) => handleCheckboxChange(e, i, "partidas_gm")}
        />
      {/snippet}
      {#snippet actionsCell(row: EditPlayerRow, i: number)}
        <Button
          variant="ghost"
          destructive={true}
          size="sm"
          iconOnly={true}
          title="Eliminar"
          onclick={() => handleDeletePlayer(i)}
          icon="🗑"
        />
      {/snippet}

      {@const tableColumns: ColumnDef<EditPlayerRow>[] = [
        { header: "Nombre", cell: nameInput, sticky: true },
        { header: "Exp.", cell: expCell },
        { header: "Juegos", cell: gamesInput },
        { header: "Prior.", cell: priorInput },
        { header: "Desea", cell: deseaInput },
        { header: "GM", cell: gmInput },
        { header: "", cell: actionsCell }
      ]}

      {#snippet addingRow()}
        {#if isAddingPlayer}
          <tr>
            <td
              colspan={tableColumns.length}
              style="padding: 0; position: relative;"
            >
              <div
                use:clickOutside={{ callback: () => (isAddingPlayer = false) }}
              >
                <input
                  type="text"
                  class="input-field text-strong"
                  bind:value={newPlayerSearchQuery}
                  placeholder="Escribe para buscar o agregar..."
                  use:focusOnMount
                  onkeydown={(e) => {
                    if (e.key === "Enter")
                      confirmAddPlayer(newPlayerSearchQuery);
                    if (e.key === "Escape") isAddingPlayer = false;
                  }}
                />
                {#if newPlayerSearchQuery.trim().length > 0}
                  <div class="autocomplete-dropdown">
                    {#each knownPlayers
                      .filter((n) => n
                          .toLowerCase()
                          .includes(newPlayerSearchQuery.toLowerCase()))
                      .slice(0, 10) as suggestedName (suggestedName)}
                      <button
                        type="button"
                        class="autocomplete-item"
                        onclick={() => confirmAddPlayer(suggestedName)}
                      >
                        {suggestedName}
                      </button>
                    {/each}
                  </div>
                {/if}
              </div>
            </td>
          </tr>
        {/if}
      {/snippet}

      <DataTable
        data={draftPlayers}
        columns={tableColumns}
        footerRow={addingRow}
      />
    {:else}
      <div class="empty-draft">
        <p>No hay jugadores en el borrador.</p>
        <p>Agrega jugadores manualmente o importa desde CSV.</p>
      </div>
    {/if}
  {/snippet}

  {#snippet footer()}
    <Button variant="secondary" fill={true} onclick={onCancel} disabled={saving}
      >Cancelar</Button
    >
    <Button
      variant="primary"
      fill={true}
      icon={saving ? "⏳" : "✨"}
      onclick={handleSave}
      disabled={saving || draftPlayers.length === 0}
      title={draftPlayers.length === 0
        ? "Agrega al menos un jugador para guardar"
        : ""}
      >{saving
        ? "Guardando..."
        : eventType === "sync"
          ? "Guardar Sincronización"
          : parentId
            ? "Guardar Edición"
            : "Guardar Nueva Lista"}</Button
    >
  {/snippet}
</PanelLayout>

{#if showCsvModal}
  <CsvImportModal onImport={handleImportCsv} onCancel={handleCancelCsv} />
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

  .empty-draft {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 40px;
    color: var(--muted);
    margin-bottom: 10px;
  }

  /* Autocomplete Dropdown Styling */
  .autocomplete-dropdown {
    position: absolute;
    bottom: 100%;
    left: 0;
    margin-bottom: 4px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    z-index: 9999;
    max-height: 200px;
    overflow-y: auto;
    width: 100%;
    box-shadow: var(--shadow-lg);
  }

  .autocomplete-item {
    padding: 8px 12px;
    cursor: pointer;
    border: none;
    border-bottom: 1px solid var(--border-subtle);
    background: transparent;
    width: 100%;
    text-align: left;
    color: var(--text-primary);
    font-size: 13px;
    font-family: inherit;
    transition: background-color var(--transition-fast);
  }

  .autocomplete-item:last-child {
    border-bottom: none;
  }

  .autocomplete-item:hover,
  .autocomplete-item:focus {
    background: var(--bg-tertiary);
    outline: none;
  }

  .empty-draft p {
    font-size: 13px;
    margin: 0;
  }
</style>
