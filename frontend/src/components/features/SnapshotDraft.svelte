<script lang="ts">
  import { onMount, tick, untrack } from "svelte";
  import { SvelteSet } from "svelte/reactivity";
  import type {
    EditPlayerRow,
    SimilarName,
    MergePair,
    NotionPlayer,
    AutocompletePlayer,
  } from "../../types";

  type CsvPlayerRow = {
    nombre: string;
    experiencia?: string;
    juegos_este_ano?: number;
    prioridad?: number;
    partidas_deseadas?: number;
    partidas_gm?: number;
    notion_id?: string | null;
    notion_name?: string | null;
    notion_alias?: string[] | null;
  };

  import { buildPlayerRow } from "../../snapshotUtils";
  import PlayerName from "../ui/PlayerName.svelte";
  import {
    saveSnapshot,
    fetchNotionPlayers,
    lookupPlayerHistory,
    getAllPlayers,
    checkPlayerSimilarity,
  } from "../../api";
  import { parsePlayersCsv, normalizeName } from "../../utils";
  import { setActiveNodeId } from "../../stores.svelte";
  import { applySyncMerges } from "../../syncUtils";
  import { clickOutside } from "../../clickOutside";
  import SyncResolutionModal from "../modals/SyncResolutionModal.svelte";
  import CsvImportModal from "../modals/CsvImportModal.svelte";
  import Button from "../ui/Button.svelte";
  import PanelLayout from "../layout/PanelLayout.svelte";
  import Badge from "../ui/Badge.svelte";
  import Tooltip from "../ui/Tooltip.svelte";
  import DataTable, { type ColumnDef } from "../layout/DataTable.svelte";
  import SectionTitle from "../ui/SectionTitle.svelte";

  let resolutionModal: ReturnType<typeof SyncResolutionModal>;

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

  let draftPlayers: EditPlayerRow[] = $state(
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
        notion_id: p.notion_id ?? null,
        notion_name: p.notion_name ?? null,
      })),
    ),
  );
  let eventType = $state(untrack(() => defaultEventType));
  let knownPlayers: AutocompletePlayer[] = $state([]);
  let activeSuggestionIndex = $state(-1);
  let isAddingPlayer = $state(false);
  let newPlayerSearchQuery = $state("");
  let pendingCsvPlayers: CsvPlayerRow[] = $state([]);
  let pendingInlinePlayer: string | null = $state(null);
  let showCsvModal = $state(false);
  let saving = $state(false);
  let isImporting = $state(false);
  let resolutionVisible = $state(false);
  let resolutionPairs = $state<SimilarName[]>([]);
  let fetchedNotionPlayers = $state<NotionPlayer[]>([]);

  // Derived state for the autocomplete dropdown. Automatically filters by text and hides already-linked identities.
  let suggestedPlayers = $derived.by(() => {
    const query = newPlayerSearchQuery.trim().toLowerCase();
    if (!query) return [];

    return knownPlayers
      .filter((player) => {
        if (!player.display.toLowerCase().includes(query)) return false;

        return !draftPlayers.some(
          (p) =>
            p.nombre === player.nombre ||
            (player.notion_id && p.notion_id === player.notion_id), // Fixed
        );
      })
      .slice(0, 10);
  });

  // Derived state for editing vs creating context
  let isEditing = $derived(parentId !== null);
  let headerTitle = $derived(
    isEditing ? `Editando Snapshot #${parentId}` : "Nueva Lista",
  );
  let headerSubtitle = $derived(
    isEditing
      ? "Modifica los jugadores, su experiencia o prioridad para esta versión."
      : "Crea una nueva versión desde cero o importa jugadores desde CSV.",
  );
  let saveButtonText = $derived.by(() => {
    if (saving) return "Guardando...";
    if (eventType === "sync") return "Guardar Sincronización";
    if (isEditing) return "Guardar Cambios";
    return "Crear Versión";
  });

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
        knownPlayers = res.players;
      })
      .catch(console.error);
  });

  function handleAddPlayer(): void {
    isAddingPlayer = true;
    newPlayerSearchQuery = "";
  }

  function focusOnMount(node: HTMLInputElement) {
    node.focus();
  }

  function enrichSimilaritiesWithDraft(
    similarities: SimilarName[],
  ): SimilarName[] {
    return similarities.map((sim) => {
      if (sim.notion_id) {
        const draftMatch = draftPlayers.find(
          (p) => p.notion_id === sim.notion_id,
        );
        if (draftMatch) {
          return { ...sim, existing_local_name: draftMatch.nombre };
        }
      }
      return sim;
    });
  }

  async function confirmAddPlayer(
    input: string | AutocompletePlayer,
    skipSimilarity: boolean = false,
    silentDuplicate: boolean = false,
  ): Promise<void> {
    // 1. Normalize input (Handle both string and rich objects)
    const isRawString = typeof input === "string";
    const name = isRawString ? input : input.nombre;

    if (!name.trim()) {
      isAddingPlayer = false;
      return;
    }

    // 2. Prevent Duplicates
    if (
      draftPlayers.some((p) => normalizeName(p.nombre) === normalizeName(name))
    ) {
      if (!silentDuplicate) {
        onShowError(
          "Jugador duplicado",
          `El jugador '${name}' ya está en la lista.`,
        );
      }
      isAddingPlayer = false;
      newPlayerSearchQuery = "";
      activeSuggestionIndex = -1;
      return;
    }

    // 3. Similarity Check (Only for raw strings)
    if (isRawString && !skipSimilarity) {
      try {
        const checkRes = await checkPlayerSimilarity([name]);
        if (checkRes.similarities && checkRes.similarities.length > 0) {
          pendingInlinePlayer = name;
          resolutionPairs = enrichSimilaritiesWithDraft(checkRes.similarities);
          resolutionVisible = true;
          return; // Stop here; the modal will call handleResolutionComplete
        }
      } catch (e) {
        console.error("Similarity check failed", e);
      }
    }

    // 4. Fetch History (Wait for data to prevent UI flickering)
    let historyData: Partial<
      EditPlayerRow & { source: "history" | "notion" | "default" }
    > = {};
    const notionId = isRawString ? undefined : input.notion_id;

    try {
      const response = await lookupPlayerHistory(
        name,
        notionId,
        parentId || undefined,
      );
      if (response.player) {
        historyData = response.player;
      }
    } catch (e) {
      console.warn("Failed to lookup player history:", e);
    }

    // 5. Construct the perfect, fully-populated row
    const baseInput = isRawString
      ? { nombre: name }
      : {
          nombre: name,
          notion_id: input.notion_id,
          notion_name: input.notion_name,
        };

    const newPlayer = buildPlayerRow(baseInput, historyData);

    // 6. Push to Svelte State
    draftPlayers = [newPlayer, ...draftPlayers];

    // 7. Reset UI
    isAddingPlayer = false;
    newPlayerSearchQuery = "";
    activeSuggestionIndex = -1;
  }

  function handleDeletePlayer(index: number): void {
    draftPlayers.splice(index, 1);
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
        resolutionPairs = enrichSimilaritiesWithDraft(checkRes.similarities);
        resolutionVisible = true;
        return;
      }
    } catch (e) {
      console.error("Similarity check failed", e);
    }

    await applyFinalCsvPlayers(parsed);
  }

  async function applyFinalCsvPlayers(parsedRows: CsvPlayerRow[]) {
    const uniqueRows: CsvPlayerRow[] = [];
    const seenNames = new SvelteSet(
      draftPlayers.map((p) => normalizeName(p.nombre)),
    );
    for (const row of parsedRows) {
      const normName = normalizeName(row.nombre);
      if (!seenNames.has(normName)) {
        uniqueRows.push(row);
        seenNames.add(normName);
      }
    }

    if (uniqueRows.length === 0) {
      showCsvModal = false;
      isImporting = false;
      return;
    }

    const playerPromises = uniqueRows.map(async (p) => {
      let historyData: Partial<
        EditPlayerRow & { source: "history" | "notion" | "default" }
      > = {};
      try {
        const response = await lookupPlayerHistory(
          p.nombre,
          p.notion_id ?? undefined,
          parentId || undefined,
        );
        if (response.player) historyData = response.player;
      } catch (e) {
        console.warn(`Failed to lookup player ${p.nombre}:`, e);
      }
      return buildPlayerRow(p, historyData);
    });

    const enhancedPlayers = await Promise.all(playerPromises);
    draftPlayers = [...draftPlayers, ...enhancedPlayers];
    showCsvModal = false;
    isImporting = false;
  }

  function handleCancelCsv(): void {
    showCsvModal = false;
  }

  async function handleImportNotion(): Promise<void> {
    isImporting = true;
    try {
      const unlinkedNames = draftPlayers
        .filter((p) => !p.notion_id)
        .map((p) => p.nombre);
      const response = await fetchNotionPlayers(unlinkedNames);

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
    // 1. Apply merges and deduplicate existing draft players
    draftPlayers = applySyncMerges(draftPlayers, merges, fetchedNotionPlayers);

    // 2. Strict Roster Rule: Add new players only if creating from scratch
    if (parentId === null) {
      const existingNames = new Set(
        draftPlayers.map((p) => normalizeName(p.nombre)),
      );
      const linkedNotionIds = new Set(
        draftPlayers.map((p) => p.notion_id).filter(Boolean),
      );

      const newPlayers = fetchedNotionPlayers
        .filter(
          (p) =>
            !linkedNotionIds.has(p.notion_id) &&
            !existingNames.has(normalizeName(p.nombre)),
        )
        .map((p) => ({
          ...p, // Spread Notion stats (experiencia, juegos_este_ano)
          original_nombre: p.nombre,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
          notion_id: p.notion_id || null,
          notion_name: p.nombre || null,
          notion_alias: p.alias || null,
          historyRestored: false,
        }));

      draftPlayers.push(...newPlayers);
    }

    eventType = "sync";
    resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
  }

  async function handleResolutionComplete(merges: MergePair[]): Promise<void> {
    resolutionVisible = false;
    if (pendingCsvPlayers.length > 0) {
      const renameActions = ["link_rename", "merge_notion", "use_existing"];
      const resolvedRows = pendingCsvPlayers.map((row) => {
        const mergeTarget = merges.find((m) => m.from === row.nombre);
        if (mergeTarget) {
          const shouldRename = renameActions.includes(mergeTarget.action);
          return {
            ...row,
            nombre: shouldRename ? mergeTarget.to : row.nombre,
            notion_name: mergeTarget.to,
            notion_id: mergeTarget.notion_id,
          };
        }
        return row;
      });
      pendingCsvPlayers = [];
      await applyFinalCsvPlayers(resolvedRows);
    } else if (pendingInlinePlayer) {
      const originalName = pendingInlinePlayer;
      pendingInlinePlayer = null;

      const mergeTarget = merges.find((m) => m.from === originalName);

      if (!mergeTarget) {
        // Action was "skip" - add as new distinct player
        await confirmAddPlayer(originalName, true);
      } else {
        // They chose a resolution ("use_existing", "link_rename", "link_only")
        const renameActions = ["link_rename", "merge_notion", "use_existing"];
        const shouldRename = renameActions.includes(mergeTarget.action);
        const isUseExisting = mergeTarget.action === "use_existing";

        const finalName = shouldRename ? mergeTarget.to : originalName;

        const playerObj = {
          display: finalName,
          nombre: finalName,
          notion_id: mergeTarget.notion_id,
          notion_name: isUseExisting ? undefined : mergeTarget.to,
          is_local: true,
          is_alias: false,
        } as AutocompletePlayer;

        await confirmAddPlayer(playerObj, true, isUseExisting);
      }
    } else {
      // It's a Notion Sync resolution
      mergeNotionPlayers(merges);
    }
  }

  function handleResolutionCancel(): void {
    resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
    pendingInlinePlayer = null;
    pendingCsvPlayers = [];
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
        .filter(
          (p): p is EditPlayerRow & { original_nombre: string } =>
            p.original_nombre !== undefined && p.original_nombre !== p.nombre,
        )
        .map((p) => ({ from: p.original_nombre, to: p.nombre }));

      const players: EditPlayerRow[] = draftPlayers.map((p) => ({
        nombre: p.nombre,
        notion_id: p.notion_id,
        notion_name: p.notion_name,
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
    draftPlayers[index]![field] = cb.checked ? 1 : 0;
  }

  function handleNumberChange(
    e: Event,
    index: number,
    field: "juegos_este_ano" | "partidas_deseadas",
  ): void {
    const input = e.target as HTMLInputElement;
    draftPlayers[index]![field] = parseInt(input.value, 10) || 0;
  }

  function handleInputKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      if (
        activeSuggestionIndex >= 0 &&
        activeSuggestionIndex < suggestedPlayers.length
      ) {
        const selectedPlayer = suggestedPlayers[activeSuggestionIndex];
        if (selectedPlayer) {
          confirmAddPlayer(selectedPlayer, true);
        } else {
          confirmAddPlayer(newPlayerSearchQuery);
        }
      } else {
        confirmAddPlayer(newPlayerSearchQuery);
      }
    } else if (e.key === "Escape") {
      isAddingPlayer = false;
      activeSuggestionIndex = -1;
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (suggestedPlayers.length > 0) {
        activeSuggestionIndex =
          (activeSuggestionIndex + 1) % suggestedPlayers.length;
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (suggestedPlayers.length > 0) {
        activeSuggestionIndex =
          activeSuggestionIndex <= 0
            ? suggestedPlayers.length - 1
            : activeSuggestionIndex - 1;
      }
    }
  }
</script>

<PanelLayout scrollable={false}>
  {#snippet header()}
    <div class="section draft-header">
      <SectionTitle title={headerTitle} />
      <div class="node-meta">
        {headerSubtitle}
      </div>
      <div class="action-row">
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
    <SectionTitle
      title="Jugadores"
      count={draftPlayers.length}
      class="compact-title"
    />
  {/snippet}

  {#snippet body()}
    {#snippet nameInput(row: EditPlayerRow, i: number)}
      <div class="name-input-wrapper">
        <PlayerName
          bind:player={draftPlayers[i]!}
          editable={true}
          showNotionIndicator={true}
        />

        {#if draftPlayers[i]?.historyRestored}
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
        style="width: var(--space-48);"
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
        style="width: var(--space-48);"
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
                onkeydown={handleInputKeydown}
              />
              {#if newPlayerSearchQuery.trim().length > 0 && suggestedPlayers.length > 0}
                <div class="autocomplete-dropdown">
                  {#each suggestedPlayers as suggestion, index (suggestion.display)}
                    <button
                      type="button"
                      class="autocomplete-item"
                      class:active={activeSuggestionIndex === index}
                      onclick={() => confirmAddPlayer(suggestion, true)}
                    >
                      {suggestion.display}
                      {#if suggestion.is_alias && suggestion.notion_name}
                        <span class="alias-text text-gray-400">
                          ↪ {suggestion.notion_name}</span
                        >
                      {/if}
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          </td>
        </tr>
      {/if}
    {/snippet}

    {#snippet emptyState()}
      {#if draftPlayers.length === 0 && !isAddingPlayer}
        <tr>
          <td
            colspan={tableColumns.length}
            style="padding: var(--space-40) var(--space-16); text-align: center; color: var(--text-muted);"
          >
            <div style="font-size: 13px; margin-bottom: var(--space-8);">
              No hay jugadores en el borrador.
            </div>
            <div style="font-size: 13px;">
              Agrega jugadores manualmente o importa desde CSV.
            </div>
          </td>
        </tr>
      {/if}
    {/snippet}

    <DataTable
      data={draftPlayers}
      columns={tableColumns}
      headerRow={addingRow}
      footerRow={emptyState}
    />
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
        : ""}>{saveButtonText}</Button
    >
  {/snippet}
</PanelLayout>

{#if showCsvModal}
  <CsvImportModal onImport={handleImportCsv} onCancel={handleCancelCsv} />
{/if}

<SyncResolutionModal
  bind:this={resolutionModal}
  visible={resolutionVisible}
  pairs={resolutionPairs}
  onComplete={handleResolutionComplete}
  onCancel={handleResolutionCancel}
/>

<style>
  .draft-header {
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
  }

  .action-row {
    display: flex;
    gap: var(--space-8);
  }

  .name-input-wrapper {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    min-width: 0; /* CRITICAL: Allows the grid column to squish this container */
  }

  /* CRITICAL: Forces the PlayerName flex child to shrink so the input doesn't stretch the grid */
  .name-input-wrapper :global(.player-name-wrapper) {
    flex: 1;
    min-width: 0;
  }

  :global(.compact-title) {
    margin-bottom: var(--space-8) !important;
  }

  /* Autocomplete Dropdown Styling */
  .autocomplete-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: var(--space-4);
    background: var(--bg-secondary);
    border: 1px solid var(--border-default);
    border-radius: var(--space-8);
    z-index: 9999;
    max-height: calc(var(--space-8) * 25);
    overflow-y: auto;
    width: 100%;
    box-shadow: var(--shadow-lg);
  }

  .autocomplete-item {
    padding: var(--space-8) var(--space-16);
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

  .autocomplete-item.active {
    background: var(--bg-tertiary);
    outline: 2px solid var(--accent-primary);
    outline-offset: -2px;
  }

  .alias-text {
    color: var(--text-muted);
    font-size: 11px;
    margin-left: var(--space-8);
    font-style: italic;
  }
</style>
