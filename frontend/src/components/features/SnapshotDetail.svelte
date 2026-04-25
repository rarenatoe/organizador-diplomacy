<script lang="ts">
  import type { EditPlayerRow, OrganizarValidation } from "../../types";
  import type { MergePair } from "../../syncResolution";
  import { setActiveNodeId } from "../../stores.svelte";
  import { validateOrganizar, applySyncMerges } from "../../syncUtils";
  import OrganizarConfirmModal from "../modals/OrganizarConfirmModal.svelte";
  import Button from "../ui/Button.svelte";
  import PanelLayout from "../layout/PanelLayout.svelte";
  import Badge from "../ui/Badge.svelte";
  import DataTable, { type ColumnDef } from "../layout/DataTable.svelte";
  import SectionTitle from "../ui/SectionTitle.svelte";
  import PlayerName from "../ui/PlayerName.svelte";
  import SnapshotHistory from "./SnapshotHistory.svelte";
  import { logger } from "../../utils/logger";
  import SyncResolutionModal from "../modals/SyncResolutionModal.svelte";
  import {
    apiPlayerRename,
    type PlayerData,
    apiSnapshot,
    apiSnapshotSave,
    type SimilarName,
    type SnapshotSaveEventType,
    type SnapshotDetailResponse,
    apiNotionFetch,
    type NotionPlayerData,
  } from "../../generated-api";
  import { parseApiError } from "../../utils";

  interface Props {
    id: number;
    onClose: () => void;
    onChainUpdate: () => void;
    onOpenSnapshot: (id: number) => void;
    onOpenGame: (id: number) => void;
    onOpenGameDraft: (snapshotId: number) => void;
    onEditDraft: (
      parentId: number,
      eventType: SnapshotSaveEventType,
      autoAction?: "notion" | "csv" | null,
      players?: EditPlayerRow[],
    ) => void;
    onShowError: (title: string, output: string) => void;
    onShowToast: (message: string) => void;
  }

  let {
    id,
    onChainUpdate,
    onOpenSnapshot,
    onOpenGameDraft,
    onEditDraft,
    onShowError,
    onShowToast,
  }: Props = $props();

  let snapshotDetail = $state<SnapshotDetailResponse | undefined>(undefined);
  const ui = $state({
    loading: true,
    isSyncing: false,
    resolutionVisible: false,
    showConfirm: false,
    csvCopied: false,
  });
  let resolutionPairs = $state<SimilarName[]>([]);
  let fetchedNotionPlayers = $state<NotionPlayerData[]>([]);
  let validation = $state<OrganizarValidation | null>(null);

  const CSV_COLS = {
    nombre: "nombre",
    is_new: "is_new",
    juegos_este_ano: "juegos_este_ano",
    prioridad: "has_priority",
    partidas_deseadas: "partidas_deseadas",
    partidas_gm: "partidas_gm",
  } as const;

  function sourceLabel(source: string | undefined): string {
    if (source === "notion_sync") return "☁️ Notion Sync";
    if (source === "organizar") return "▶ Organizar";
    return "📥 Manual";
  }

  const csvText = $derived(() => {
    if (!snapshotDetail?.players) return "";
    const rows = snapshotDetail.players;
    return [
      Object.keys(CSV_COLS).join(","),
      ...rows.map((r) =>
        Object.values(CSV_COLS)
          .map((c) => {
            const value = r[c];
            if (c === "is_new") {
              return value ? "Nuevo" : "Antiguo";
            }
            return String(value ?? "");
          })
          .join(","),
      ),
    ].join("\n");
  });

  const playersForDraft = $derived(() => {
    return (snapshotDetail?.players || []).map((p) => ({
      nombre: p.nombre,
      is_new: p.is_new ?? true,
      juegos_este_ano: p.juegos_este_ano ?? 0,
      has_priority: p.has_priority ?? false,
      partidas_deseadas: p.partidas_deseadas ?? 1,
      partidas_gm: p.partidas_gm ?? 0,
      notion_id: p.notion_id ?? null,
      notion_name: p.notion_name ?? null,
    }));
  });

  async function loadSnapshot(): Promise<void> {
    ui.loading = true;
    try {
      const { data, error } = await apiSnapshot({ path: { snapshot_id: id } });
      if (error) {
        onShowError("Error al cargar snapshot", parseApiError(error));
        snapshotDetail = undefined;
        return;
      }
      if (!data) {
        onShowError(
          "Error al cargar snapshot",
          "La respuesta del snapshot no contiene datos.",
        );
        snapshotDetail = undefined;
        return;
      }
      snapshotDetail = data;
      logger.info("Loaded snapshot data:", data);
    } catch (e) {
      onShowError("Error de conexión", String(e));
      snapshotDetail = undefined;
    } finally {
      ui.loading = false;
    }
  }

  async function copyCsv(): Promise<void> {
    await navigator.clipboard.writeText(csvText());
    ui.csvCopied = true;
    setTimeout(() => {
      ui.csvCopied = false;
    }, 1500);
  }

  async function handleOrganizar(): Promise<void> {
    if (!snapshotDetail?.players) return;

    if (snapshotDetail.players.length < 7) {
      onShowError(
        "Error al organizar",
        "Se necesitan al menos 7 jugadores para organizar partidas.",
      );
      return;
    }

    validation = validateOrganizar(snapshotDetail.players);
    if (validation) {
      ui.showConfirm = true;
    } else {
      await executeOrganizar();
    }
  }

  async function executeOrganizar(): Promise<void> {
    ui.showConfirm = false;
    // Open the game draft panel instead of running the script directly
    onOpenGameDraft(id);
  }

  async function handleDirectSync(): Promise<void> {
    ui.isSyncing = true;
    try {
      const unlinkedNames =
        snapshotDetail?.players
          ?.filter((p) => !p.notion_id)
          .map((p) => p.nombre) || [];
      const response = await apiNotionFetch({
        body: { snapshot_names: unlinkedNames },
      });

      if (response.error) {
        onShowError("Error de Sincronización", parseApiError(response.error));
        ui.isSyncing = false;
        return;
      }

      fetchedNotionPlayers = response.data?.players ?? [];

      if ((response.data?.similar_names?.length ?? 0) > 0) {
        // Show resolution modal - isSyncing remains true until modal completes
        resolutionPairs = response.data?.similar_names ?? [];
        ui.resolutionVisible = true;
      } else {
        // No conflicts, merge directly - executeSyncMerge will handle isSyncing reset
        await executeSyncMerge([]);
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
      ui.isSyncing = false;
    }
  }

  async function handleResolutionComplete(merges: MergePair[]): Promise<void> {
    try {
      // 1. Process collision merges first via rename endpoint
      const collisionMerges = merges.filter((m) => m.action === "merge_local");
      for (const merge of collisionMerges) {
        const res = await apiPlayerRename({
          body: { old_name: merge.from, new_name: merge.to },
        });
        if (res.error) {
          onShowError("Error al fusionar", parseApiError(res.error));
          return;
        }
      }

      // 3. Execute sync merge for all actions to update the DB and reload
      await executeSyncMerge(merges);
    } catch (e) {
      onShowError("Error al procesar resolución", String(e));
    }

    // Reset visibility state at the end
    ui.resolutionVisible = false;
    if ("isSyncing" in ui) ui.isSyncing = false; // Only needed in Detail, safe for Draft
  }

  async function executeSyncMerge(merges: MergePair[]): Promise<void> {
    // Extract renames payload for the backend diff algorithm
    const renameActions = ["link_rename", "merge_local", "use_existing"];
    const renamesPayload = merges
      .filter((m) => renameActions.includes(m.action))
      .map((m) => ({ old_name: m.from, new_name: m.to }));

    const deduplicatedPlayers = applySyncMerges(
      snapshotDetail?.players || [],
      merges,
      fetchedNotionPlayers,
    );

    try {
      const { data, error } = await apiSnapshotSave({
        method: "POST",
        body: {
          parent_id: id,
          event_type: "sync",
          players: deduplicatedPlayers,
          renames: renamesPayload,
        },
      });

      if (error) {
        const errorMessage = parseApiError(error);
        if (errorMessage.includes("ya fue generado por notion_sync")) {
          onShowToast("⚠️ " + errorMessage);
        } else {
          onShowError("Error de Sincronización", errorMessage);
        }
        return;
      }

      // Handle no_changes response
      if (data.status === "no_changes") {
        onShowToast("Notion ya está actualizado (sin cambios detectados)");
        return;
      }

      // Only trigger updates if the sync was successful
      await loadSnapshot(); // Force reactive update with new data
      onChainUpdate();
      if (data.snapshot_id !== undefined) {
        setActiveNodeId(data.snapshot_id);
        onOpenSnapshot(data.snapshot_id);
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
    } finally {
      // Reset all sync-related state
      ui.resolutionVisible = false;
      resolutionPairs = [];
      fetchedNotionPlayers = [];
      ui.isSyncing = false;
    }
  }

  function handleResolutionCancel(): void {
    ui.resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
    ui.isSyncing = false;
  }

  $effect(() => {
    void loadSnapshot();
  });
</script>

{#if ui.loading}
  <p class="loading-text">Cargando…</p>
{:else if snapshotDetail}
  {@const rows = snapshotDetail.players ?? []}
  <PanelLayout scrollable={false}>
    {#snippet header()}
      <div class="section snapshot-header">
        <div class="header-row">
          <div>
            <SectionTitle
              title={`Snapshot #${id} · ${sourceLabel(snapshotDetail?.source)}`}
              class="header-title"
            />
            <div class="meta-data">
              {snapshotDetail?.created_at}
            </div>
          </div>
          <Button
            size="sm"
            variant={ui.csvCopied ? "success" : "secondary"}
            icon={ui.csvCopied ? "✅" : "📋"}
            onclick={copyCsv}
            style="min-width: calc(var(--space-8) * 15);"
            >{ui.csvCopied ? "Copiado" : "Copiar CSV"}</Button
          >
        </div>
      </div>
      <SectionTitle
        title="Jugadores"
        count={rows.length}
        class="compact-title"
      />
    {/snippet}

    {#snippet body()}
      {#snippet nameCell(row: PlayerData)}
        <PlayerName player={row} editable={false} showNotionIndicator={true} />
      {/snippet}

      {#snippet expCell(row: PlayerData, _index: number)}
        {#if row.is_new !== undefined}
          <Badge
            variant={row.is_new ? "warning" : "success"}
            text={row.is_new ? "Nuevo" : "Antiguo"}
            fixedWidth={true}
          />
        {/if}
      {/snippet}

      {#snippet priorCell(row: PlayerData, _index: number)}
        {row.has_priority ? "✓" : ""}
      {/snippet}

      {#snippet gmCell(row: PlayerData, _index: number)}
        {row.partidas_gm > 0 ? "✓" : ""}
      {/snippet}

      {@const tableColumns: ColumnDef<PlayerData>[] = [
    { header: "Nombre", cell: nameCell, sticky: true },
    { header: "Exp.", cell: expCell },
    { header: "Juegos", key: "juegos_este_ano" },
    { header: "Prior.", cell: priorCell },
    { header: "Desea", key: "partidas_deseadas" },
    { header: "GM", cell: gmCell }
  ]}

      <DataTable data={rows} columns={tableColumns} />
      {#if snapshotDetail?.history && snapshotDetail.history.length > 0}
        <SnapshotHistory history={snapshotDetail.history} />
      {/if}
    {/snippet}
    {#snippet footer()}
      <Button
        variant="secondary"
        fill={true}
        icon="📝"
        onclick={() => {
          onEditDraft(id, "manual", null, playersForDraft());
        }}>Editar</Button
      >
      <Button
        variant="secondary"
        fill={true}
        icon="🔄"
        onclick={handleDirectSync}
        disabled={ui.isSyncing}
        >{ui.isSyncing ? "Sincronizando..." : "Sincronizar Notion"}</Button
      >
      <Button variant="primary" fill={true} icon="▶️" onclick={handleOrganizar}
        >Organizar Partidas</Button
      >
    {/snippet}
  </PanelLayout>
{/if}

<SyncResolutionModal
  visible={ui.resolutionVisible}
  pairs={resolutionPairs}
  onComplete={handleResolutionComplete}
  onCancel={handleResolutionCancel}
/>

<OrganizarConfirmModal
  visible={ui.showConfirm}
  {validation}
  onConfirm={executeOrganizar}
  onEdit={() => {
    ui.showConfirm = false;
    onEditDraft(id, "manual", null, playersForDraft());
  }}
  onCancel={() => {
    ui.showConfirm = false;
  }}
/>

<style>
  .snapshot-header {
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
  }

  .header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--space-4);
  }

  .meta-data {
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 400;
  }

  .header-row :global(.section-title) {
    margin-bottom: 0;
  }
</style>
