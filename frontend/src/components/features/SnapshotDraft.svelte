<script lang="ts">
  import { onMount, untrack } from "svelte";
  import { SvelteSet } from "svelte/reactivity";

  import { clickOutside } from "../../clickOutside";
  import {
    apiNotionFetch,
    apiPlayerCheckSimilarity,
    apiPlayerGetAll,
    apiPlayerLookup,
    apiSnapshotSave,
    type NotionPlayerData,
    type PlayerAutocompleteItem,
    type PlayerHistoryItem,
    type PlayerSimilarityItem,
    type SnapshotSaveEventType,
  } from "../../generated-api";
  import { buildPlayerRow } from "../../snapshotUtils";
  import { setActiveNodeId } from "../../stores.svelte";
  import type { MergePair } from "../../syncResolution";
  import { applySyncMerges } from "../../syncUtils";
  import type { EditPlayerRow } from "../../types";
  import { normalizeName, parseApiError, parsePlayersCsv } from "../../utils";
  import DataTable, { type ColumnDef } from "../layout/DataTable.svelte";
  import PanelLayout from "../layout/PanelLayout.svelte";
  import PanelSection from "../layout/PanelSection.svelte";
  import CsvImportModal from "../modals/CsvImportModal.svelte";
  import SyncResolutionModal from "../modals/SyncResolutionModal.svelte";
  import Badge from "../ui/Badge.svelte";
  import Button from "../ui/Button.svelte";
  import PlayerName from "../ui/PlayerName.svelte";
  import SectionTitle from "../ui/SectionTitle.svelte";
  import Tooltip from "../ui/Tooltip.svelte";
  import PlayerAutocompleteInput from "./PlayerAutocompleteInput.svelte";

  type CsvPlayerRow = {
    nombre: string;
    is_new?: boolean;
    juegos_este_ano?: number;
    has_priority?: boolean;
    partidas_deseadas?: number;
    partidas_gm?: number;
    notion_id?: string | null;
    notion_name?: string | null;
    notion_alias?: string[] | null;
  };

  const DEFAULT_PLAYER_HISTORY: PlayerHistoryItem = {
    source: "default",
    is_new: true,
    juegos_este_ano: 0,
    has_priority: false,
    partidas_deseadas: 1,
    partidas_gm: 0,
  };

  interface Props {
    parentId: number | null;
    initialPlayers: EditPlayerRow[];
    saveEventType: SnapshotSaveEventType;
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
    saveEventType: initialSaveEventType,
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
        oldName: p.nombre, // Track original name for rename detection
        is_new: p.is_new ?? true,
        juegos_este_ano: p.juegos_este_ano ?? 0,
        has_priority: p.has_priority,
        partidas_deseadas: p.partidas_deseadas,
        partidas_gm: p.partidas_gm,
        historyRestored: false, // Default for existing players
        notion_id: p.notion_id ?? null,
        notion_name: p.notion_name ?? null,
      })),
    ),
  );
  let saveEventType = $state(untrack(() => initialSaveEventType));
  let knownPlayers: PlayerAutocompleteItem[] = $state([]);
  let isAddingPlayer = $state(false);
  let newPlayerSearchQuery = $state("");
  let pendingCsvPlayers: CsvPlayerRow[] = $state([]);
  let showCsvModal = $state(false);
  let saving = $state(false);
  let isImporting = $state(false);
  let resolutionVisible = $state(false);
  let resolutionPairs = $state<Array<PlayerSimilarityItem>>([]);
  let fetchedNotionPlayers = $state<NotionPlayerData[]>([]);

  // Derived state for editing vs creating context
  let isEditing = $derived(parentId !== null);
  let headerTitle = $derived(
    isEditing ? `Editando Snapshot #${parentId}` : "Nueva Lista",
  );
  let headerSubtitle = $derived(
    isEditing
      ? "Modifica los jugadores, su is_new o has_priority para esta versión."
      : "Crea una nueva lista desde cero o importa jugadores desde CSV.",
  );

  let saveButtonText = $derived.by(() => {
    if (saving) return "Guardando...";
    if (saveEventType === "sync") return "Guardar Sincronización";
    if (isEditing) return "Guardar Cambios";
    return "Crear Lista";
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
    apiPlayerGetAll()
      .then((res) => {
        knownPlayers = res.data?.players ?? [];
      })
      .catch(console.error);
  });

  function handleAddPlayer(): void {
    isAddingPlayer = true;
    newPlayerSearchQuery = "";
  }

  function enrichSimilaritiesWithDraft(
    similarities: Array<PlayerSimilarityItem>,
  ): Array<PlayerSimilarityItem> {
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
    input: string | PlayerAutocompleteItem,
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
      return;
    }

    // 3. Fetch History (Wait for data to prevent UI flickering)
    let historyData: PlayerHistoryItem = DEFAULT_PLAYER_HISTORY;

    try {
      const response = await apiPlayerLookup({
        body: {
          name,
          notion_id: isRawString ? undefined : input.notion_id,
          snapshot_id: parentId,
        },
      });
      if (response.data) historyData = response.data.player;
    } catch (e) {
      console.warn("Failed to lookup player history:", e);
    }

    // 4. Construct the perfect, fully-populated row
    const baseInput = isRawString
      ? { nombre: name }
      : {
          nombre: input.nombre,
          notion_id: input.notion_id,
          notion_name: input.notion_name,
        };

    const newPlayer = buildPlayerRow(baseInput, historyData);

    // 5. Push to Svelte State
    draftPlayers = [newPlayer, ...draftPlayers];

    // 6. Reset UI
    isAddingPlayer = false;
    newPlayerSearchQuery = "";
  }

  function handleDeletePlayer(index: number): void {
    // LLM Rule: Avoid surgical array patching. Use deterministic mapping.
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
      const checkRes = await apiPlayerCheckSimilarity({
        body: { names: playerNames },
      });
      if (checkRes.data && checkRes.data.similarities.length > 0) {
        pendingCsvPlayers = parsed;
        resolutionPairs = enrichSimilaritiesWithDraft(
          checkRes.data.similarities,
        );
        resolutionVisible = true;
        return;
      }
    } catch (e) {
      console.error("Similarity check failed", e);
    }

    await applyFinalCsvPlayers(parsed);
  }

  async function applyFinalCsvPlayers(parsedRows: CsvPlayerRow[]) {
    const seenNames = new SvelteSet(
      draftPlayers.map((p) => normalizeName(p.nombre)),
    );

    // LLM Rule: Declarative `.filter()` derivation instead of `for...of` iteration.
    const uniqueRows = parsedRows.filter((row) => {
      const normName = normalizeName(row.nombre);
      if (!seenNames.has(normName)) {
        seenNames.add(normName);
        return true;
      }
      return false;
    });

    if (uniqueRows.length === 0) {
      showCsvModal = false;
      isImporting = false;
      return;
    }

    const playerPromises = uniqueRows.map(async (p) => {
      let historyData: PlayerHistoryItem = DEFAULT_PLAYER_HISTORY;
      try {
        const response = await apiPlayerLookup({
          body: {
            name: p.nombre,
            notion_id: p.notion_id,
            snapshot_id: parentId,
          },
        });
        if (response.data) historyData = response.data.player;
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
      const response = await apiNotionFetch({
        body: { snapshot_names: unlinkedNames },
      });

      if (response.error) {
        onShowError("Aviso / Error", parseApiError(response.error));
        return;
      }

      fetchedNotionPlayers = response.data?.players ?? [];

      if ((response.data?.similar_names?.length ?? 0) > 0) {
        // Show resolution modal
        resolutionPairs = response.data?.similar_names ?? [];
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
          ...p, // Spread Notion stats (is_new, juegos_este_ano)
          oldName: p.nombre,
          has_priority: false,
          partidas_deseadas: 1,
          partidas_gm: 0,
          notion_id: p.notion_id || null,
          notion_name: p.nombre || null,
          notion_alias: p.alias || null,
          historyRestored: false,
        }));

      draftPlayers.push(...newPlayers);
    }

    saveEventType = "sync";
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
    } else {
      // It's a Notion Sync resolution
      mergeNotionPlayers(merges);
    }
  }

  function handleResolutionCancel(): void {
    resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
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
          (p): p is EditPlayerRow & { oldName: string } =>
            p.oldName !== undefined && p.oldName !== p.nombre,
        )
        .map((p) => {
          const newName = p.nombre;
          return { old_name: p.oldName, new_name: newName };
        });

      const { data, error } = await apiSnapshotSave({
        method: "POST",
        body: {
          parent_id: parentId,
          event_type: saveEventType,
          players: draftPlayers,
          renames: manualRenames,
        },
      });

      if (error) {
        onShowError("Aviso / Error", parseApiError(error));
        return;
      }

      onClose();
      onChainUpdate();
      if (data.snapshot_id !== undefined) {
        setActiveNodeId(data.snapshot_id);
        onOpenSnapshot(data.snapshot_id);
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
    field: "has_priority" | "partidas_gm",
  ): void {
    const cb = e.target as HTMLInputElement;
    const player = draftPlayers[index];
    if (player) {
      if (field === "has_priority") {
        player.has_priority = cb.checked;
      } else {
        player.partidas_gm = cb.checked ? 1 : 0;
      }
    }
  }

  function handleNumberChange(
    e: Event,
    index: number,
    field: "juegos_este_ano" | "partidas_deseadas",
  ): void {
    const input = e.target as HTMLInputElement;
    const player = draftPlayers[index];
    if (player) {
      const parsedValue = parseInt(input.value, 10);
      player[field] = !isNaN(parsedValue) ? parsedValue : 0;
    }
  }
</script>

<PanelLayout scrollable={false}>
  {#snippet header()}
    <PanelSection>
      <SectionTitle title={headerTitle} />
      <p class="node-meta-desc">{headerSubtitle}</p>
    </PanelSection>
    <PanelSection>
      <div class="action-row">
        <Button variant="secondary" fill={true} onclick={handleAddPlayer}>
          ➕ Agregar jugador
        </Button>
        {#if parentId === null}
          <Button
            variant="secondary"
            fill={true}
            onclick={() => (showCsvModal = true)}
          >
            📥 Pegar CSV
          </Button>
          <Button
            variant="secondary"
            fill={true}
            onclick={handleImportNotion}
            disabled={isImporting}
          >
            {isImporting ? "⏳ Sincronizando..." : "🔗 Importar Notion"}
          </Button>
        {/if}
      </div>
    </PanelSection>
    <SectionTitle
      title="Jugadores"
      count={draftPlayers.length}
      style="margin-bottom: var(--space-8);"
    />
  {/snippet}

  {#snippet body()}
    {#snippet nameInput(_row: EditPlayerRow, i: number)}
      {#if draftPlayers[i]}
        <div class="name-input-wrapper">
          <PlayerName
            bind:player={draftPlayers[i]}
            editable={true}
            showNotionIndicator={true}
            {knownPlayers}
            existingPlayers={draftPlayers}
          />

          {#if draftPlayers[i]?.historyRestored}
            <Tooltip
              text="Perfil histórico cargado desde la base de datos"
              icon="📚"
            />
          {/if}
        </div>
      {/if}
    {/snippet}

    {#snippet expCell(row: EditPlayerRow)}
      {#if row.is_new}
        <Badge
          variant={row.is_new ? "warning" : "success"}
          text={row.is_new ? "Nuevo" : "Antiguo"}
          fixedWidth={true}
        />
      {/if}
    {/snippet}

    {#snippet gamesInput(row: EditPlayerRow, i: number)}
      {@const handleChange = (e: Event) =>
        handleNumberChange(e, i, "juegos_este_ano")}
      <input
        type="number"
        class="table-input"
        value={row.juegos_este_ano}
        min="0"
        style="width: var(--space-48);"
        onchange={handleChange}
      />
    {/snippet}

    {#snippet priorInput(row: EditPlayerRow, i: number)}
      {@const handleChange = (e: Event) =>
        handleCheckboxChange(e, i, "has_priority")}
      <input
        type="checkbox"
        class="table-checkbox"
        checked={row.has_priority}
        onchange={handleChange}
      />
    {/snippet}

    {#snippet deseaInput(row: EditPlayerRow, i: number)}
      {@const handleChange = (e: Event) =>
        handleNumberChange(e, i, "partidas_deseadas")}
      <input
        type="number"
        class="table-input"
        value={row.partidas_deseadas}
        min="0"
        max="9"
        style="width: var(--space-48);"
        onchange={handleChange}
      />
    {/snippet}

    {#snippet gmInput(row: EditPlayerRow, i: number)}
      {@const handleChange = (e: Event) =>
        handleCheckboxChange(e, i, "partidas_gm")}
      <input
        type="checkbox"
        class="table-checkbox"
        checked={row.partidas_gm > 0}
        onchange={handleChange}
      />
    {/snippet}
    {#snippet actionsCell(_row: EditPlayerRow, i: number)}
      {@const handleDelete = () => handleDeletePlayer(i)}
      <Button
        variant="ghost"
        destructive={true}
        size="sm"
        iconOnly={true}
        title="Eliminar"
        onclick={handleDelete}
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
              <PlayerAutocompleteInput
                bind:value={newPlayerSearchQuery}
                {knownPlayers}
                existingPlayers={draftPlayers}
                onConfirm={(input, silent) => confirmAddPlayer(input, silent)}
                onClickOutside={() => (isAddingPlayer = false)}
                clearOnConfirm={true}
                autofocus={true}
                wrapperClass="autocomplete-wrapper"
              />
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
  visible={resolutionVisible}
  pairs={resolutionPairs}
  onComplete={handleResolutionComplete}
  onCancel={handleResolutionCancel}
/>

<style>
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

  .node-meta-desc {
    color: var(--text-muted);
    font-size: 13px;
    margin: 0;
  }
</style>
