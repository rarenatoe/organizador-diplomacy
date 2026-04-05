<script lang="ts">
  import type {
    SnapshotDetail,
    EditPlayerRow,
    SimilarName,
    MergePair,
    NotionPlayer,
    OrganizarValidation,
  } from "../types";
  import {
    fetchSnapshot,
    renamePlayer,
    fetchNotionPlayers,
    saveSnapshot,
  } from "../api";
  import { setActiveNodeId } from "../stores.svelte";
  import { validateOrganizar } from "../syncUtils";
  import { normalizeName } from "../utils";
  import SyncResolutionModal from "./SyncResolutionModal.svelte";
  import OrganizarConfirmModal from "./OrganizarConfirmModal.svelte";
  import Button from "./Button.svelte";
  import PanelLayout from "./PanelLayout.svelte";
  import Badge from "./Badge.svelte";
  import DataTable, { type ColumnDef } from "./DataTable.svelte";
  import SnapshotHistory from "./SnapshotHistory.svelte";
  import { logger } from "../utils/logger";

  interface Props {
    id: number;
    onClose: () => void;
    onChainUpdate: () => void;
    onOpenSnapshot: (id: number) => void;
    onOpenGame: (id: number) => void;
    onOpenGameDraft: (snapshotId: number) => void;
    onEditDraft: (
      parentId: number,
      eventType: "sync" | "manual" | "edit",
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

  let data = $state<SnapshotDetail | null>(null);
  const ui = $state({
    loading: true,
    isSyncing: false,
    resolutionVisible: false,
    showConfirm: false,
    csvCopied: false,
  });
  let resolutionPairs = $state<SimilarName[]>([]);
  let fetchedNotionPlayers = $state<NotionPlayer[]>([]);
  let validation = $state<OrganizarValidation | null>(null);

  const CSV_COLS = [
    "nombre",
    "experiencia",
    "juegos_este_ano",
    "prioridad",
    "partidas_deseadas",
    "partidas_gm",
  ] as const;

  function sourceLabel(source: string | undefined): string {
    if (source === "notion_sync") return "☁️ Notion Sync";
    if (source === "organizar") return "▶ Organizar";
    return "📥 Manual";
  }

  const csvText = $derived(() => {
    if (!data?.players) return "";
    const rows = data.players;
    return [
      CSV_COLS.join(","),
      ...rows.map((r) => CSV_COLS.map((c) => String(r[c] ?? "")).join(",")),
    ].join("\n");
  });

  const playersForDraft = $derived(() => {
    return (data?.players || []).map((p) => ({
      nombre: p.nombre,
      experiencia: p.experiencia ?? "Nuevo",
      juegos_este_ano: p.juegos_este_ano ?? 0,
      prioridad: p.prioridad ?? 0,
      partidas_deseadas: p.partidas_deseadas ?? 1,
      partidas_gm: p.partidas_gm ?? 0,
    }));
  });

  async function loadSnapshot(): Promise<void> {
    ui.loading = true;
    try {
      data = await fetchSnapshot(id);
      logger.info("Loaded snapshot data:", data);
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
    if (!data?.players) return;

    if (data.players.length < 7) {
      onShowError(
        "Error al organizar",
        "Se necesitan al menos 7 jugadores para organizar partidas.",
      );
      return;
    }

    validation = validateOrganizar(data.players);
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
    if (data?.source === "notion_sync") {
      onShowError(
        "Acción no permitida",
        "El snapshot base ya fue generado por notion_sync y aún no se ha jugado una partida.",
      );
      return;
    }

    ui.isSyncing = true;
    try {
      const currentNames = (data?.players ?? []).map((p) => p.nombre);
      const response = await fetchNotionPlayers(currentNames);

      if (response.error) {
        onShowError(
          "Error de Sincronización",
          response.error || "Error desconocido",
        );
        ui.isSyncing = false;
        return;
      }

      fetchedNotionPlayers = response.players;

      if (response.similar_names && response.similar_names.length > 0) {
        // Show resolution modal - isSyncing remains true until modal completes
        resolutionPairs = response.similar_names;
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

  async function executeSyncMerge(merges: MergePair[]): Promise<void> {
    const mergeMap = new Map(merges.map((m) => [m.from, m]));
    const currentRows = data?.players ?? [];

    // Extract renames payload for the backend diff algorithm
    const renamesPayload = merges
      .filter((m) => m.action === "merge_notion")
      .map((m) => ({ from: m.from, to: m.to }));

    // Update existing players with Notion data (Strict Roster Rule: only update existing)
    const mergedPlayers = currentRows.map((row) => {
      const currentName = row.nombre;
      const mergeInfo = mergeMap.get(currentName);
      const notionName = mergeInfo ? mergeInfo.to : currentName;
      const normName = normalizeName(notionName);

      const notionPlayer = fetchedNotionPlayers.find(
        (p) =>
          normalizeName(p.nombre) === normName ||
          p.alias?.some((a: string) => normalizeName(a) === normName),
      );

      if (notionPlayer) {
        return {
          nombre:
            mergeInfo?.action === "merge_notion"
              ? notionPlayer.nombre
              : currentName,
          experiencia: notionPlayer.experiencia,
          juegos_este_ano: notionPlayer.juegos_este_ano,
          prioridad: row.prioridad,
          partidas_deseadas: row.partidas_deseadas,
          partidas_gm: row.partidas_gm,
        };
      }
      return {
        nombre: currentName,
        experiencia: row.experiencia ?? "Nuevo",
        juegos_este_ano: row.juegos_este_ano ?? 0,
        prioridad: row.prioridad,
        partidas_deseadas: row.partidas_deseadas,
        partidas_gm: row.partidas_gm,
      };
    });

    try {
      const result = await saveSnapshot({
        parent_id: id,
        event_type: "sync",
        players: mergedPlayers,
        renames: renamesPayload,
      });

      if (result.error) {
        // Handle backend errors properly, including the Strict Guard message
        onShowError("Error de Sincronización", result.error);
        return;
      }

      // Handle no_changes response
      if (result.status === "no_changes") {
        onShowToast("Notion ya está actualizado (sin cambios detectados)");
        return;
      }

      // Only trigger updates if the sync was successful
      await loadSnapshot(); // Force reactive update with new data
      onChainUpdate();
      if (result.snapshot_id !== undefined) {
        setActiveNodeId(result.snapshot_id as number);
        onOpenSnapshot(result.snapshot_id);
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

  function handleResolutionComplete(merges: MergePair[]): void {
    void executeSyncMerge(merges);
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
  <p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>
{:else if data}
  {@const rows = data.players ?? []}
  <PanelLayout scrollable={false}>
    {#snippet header()}
      <div class="section" style="margin-bottom: 12px;">
        <div
          style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;"
        >
          <div>
            <div class="section-title" style="margin-bottom: 2px;">
              Snapshot #{id} · {sourceLabel(data?.source)}
            </div>
            <div
              class="node-meta"
              style="color: var(--muted); font-size: 11px; font-weight: 400;"
            >
              {data?.created_at}
            </div>
          </div>
          <Button
            size="sm"
            variant={ui.csvCopied ? "success" : "secondary"}
            icon={ui.csvCopied ? "✅" : "📋"}
            onclick={copyCsv}
            style="min-width: 120px;"
            >{ui.csvCopied ? "Copiado" : "Copiar CSV"}</Button
          >
        </div>
      </div>
      <div class="section-title" style="margin-bottom: 4px;">Jugadores</div>
    {/snippet}

    {#snippet body()}
      {#snippet nameCell(row: EditPlayerRow, index: number)}
        <span class="text-strong">{row.nombre}</span>
      {/snippet}

      {#snippet expCell(row: EditPlayerRow, index: number)}
        {#if row.experiencia}
          <Badge
            variant={row.experiencia === "Nuevo" ? "warning" : "success"}
            text={row.experiencia}
            fixedWidth={true}
          />
        {/if}
      {/snippet}

      {#snippet priorCell(row: EditPlayerRow, index: number)}
        {row.prioridad === 1 ? "✓" : ""}
      {/snippet}

      {#snippet gmCell(row: EditPlayerRow, index: number)}
        {row.partidas_gm > 0 ? "✓" : ""}
      {/snippet}

      {@const tableColumns: ColumnDef<EditPlayerRow>[] = [
    { header: "Nombre", cell: nameCell, sticky: true },
    { header: "Exp.", cell: expCell },
    { header: "Juegos", key: "juegos_este_ano" },
    { header: "Prior.", cell: priorCell },
    { header: "Desea", key: "partidas_deseadas" },
    { header: "GM", cell: gmCell }
  ]}

      <DataTable data={rows} columns={tableColumns} />
      {#if data?.history && data.history.length > 0}
        <SnapshotHistory history={data.history} />
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
</style>
