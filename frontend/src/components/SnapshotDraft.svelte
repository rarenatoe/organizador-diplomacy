<script lang="ts">
  import { untrack } from "svelte";
  import type {
    EditPlayerRow,
    SimilarName,
    MergePair,
    NotionPlayer,
  } from "../types";
  import { saveSnapshot, fetchNotionPlayers } from "../api";
  import { parsePlayersCsv, normalizeName } from "../utils";
  import { setActiveNodeId } from "../stores.svelte";
  import SyncResolutionModal from "./SyncResolutionModal.svelte";
  import CsvImportModal from "./CsvImportModal.svelte";
  import Button from "./Button.svelte";
  import PanelLayout from "./PanelLayout.svelte";
  import Badge from "./Badge.svelte";
  import DataTable, { type ColumnDef } from "./DataTable.svelte";

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
      })),
    ),
  );
  let eventType = $state(untrack(() => defaultEventType));
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

  function handleAddPlayer(): void {
    const nombre = prompt("Nombre del nuevo jugador:");
    if (!nombre) return;
    draftPlayers = [
      ...draftPlayers,
      {
        nombre,
        original_nombre: nombre,
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

  function handleImportCsv(text: string): void {
    const parsed = parsePlayersCsv(text);
    if (parsed.length === 0) {
      onShowError(
        "Aviso / Error",
        "No se encontraron jugadores válidos en el CSV",
      );
      return;
    }
    draftPlayers = [
      ...draftPlayers,
      ...parsed.map((p) => ({ ...p, original_nombre: p.nombre })),
    ];
    showCsvModal = false;
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
        <input
          type="text"
          class="table-input table-input-ghost text-strong"
          bind:value={row.nombre}
          placeholder="Nombre del jugador"
        />
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

      <DataTable data={draftPlayers} columns={tableColumns} />
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

  .empty-draft p {
    font-size: 13px;
    margin: 0;
  }
</style>
