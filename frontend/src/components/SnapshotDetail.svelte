<script lang="ts">
  import type { SnapshotDetail, EditPlayerRow, SimilarName, MergePair, NotionPlayer, OrganizarValidation } from "../types";
  import { fetchSnapshot, renamePlayer, fetchNotionPlayers, saveSnapshot } from "../api";
  import { setActiveNodeId } from "../stores.svelte";
  import { validateOrganizar } from "../syncUtils";
  import { normalizeName } from "../utils";
  import SyncResolutionModal from "./SyncResolutionModal.svelte";
  import OrganizarConfirmModal from "./OrganizarConfirmModal.svelte";
  import Button from "./Button.svelte";
  import PanelLayout from "./PanelLayout.svelte";

  interface Props {
    id: number;
    onClose: () => void;
    onChainUpdate: () => void;
    onOpenSnapshot: (id: number) => void;
    onOpenGame: (id: number) => void;
    onOpenGameDraft: (snapshotId: number) => void;
    onEditDraft: (parentId: number, eventType: "sync" | "manual" | "edit", autoAction?: 'notion' | 'csv' | null, players?: EditPlayerRow[]) => void;
    onShowError: (title: string, output: string) => void;
  }

  let { id, onChainUpdate, onOpenSnapshot, onOpenGameDraft, onEditDraft, onShowError }: Props = $props();

  let data = $state<SnapshotDetail | null>(null);
  let loading = $state(true);
  let isSyncing = $state(false);
  let resolutionVisible = $state(false);
  let resolutionPairs = $state<SimilarName[]>([]);
  let fetchedNotionPlayers = $state<NotionPlayer[]>([]);
  let csvCopied = $state(false);

  let showConfirm = $state(false);
  let validation = $state<OrganizarValidation | null>(null);

  const CSV_COLS = [
    "nombre",
    "experiencia",
    "juegos_este_ano",
    "prioridad",
    "partidas_deseadas",
    "partidas_gm",
  ] as const;

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
        CSV_COLS.map((c) =>
          String(r[c] ?? ""),
        ).join(","),
      ),
    ].join("\n");
  }

  async function copyCsv(): Promise<void> {
    await navigator.clipboard.writeText(getCsvText());
    csvCopied = true;
    setTimeout(() => {
      csvCopied = false;
    }, 1500);
  }

  async function handleOrganizar(): Promise<void> {
    if (!data?.players) return;

    if (data.players.length < 7) {
      onShowError("Error al organizar", "Se necesitan al menos 7 jugadores para organizar partidas.");
      return;
    }

    validation = validateOrganizar(data.players);
    if (validation) {
      showConfirm = true;
    } else {
      await executeOrganizar();
    }
  }

  async function executeOrganizar(): Promise<void> {
    showConfirm = false;
    // Open the game draft panel instead of running the script directly
    onOpenGameDraft(id);
  }

  async function handleRename(oldName: string): Promise<void> {
    const newName = prompt(`Renombrar jugador "${oldName}" a:`, oldName);
    if (!newName || newName === oldName) return;
    const result = await renamePlayer(oldName, newName);
    if (result.error) { alert(`Error: ${result.error}`); return; }
    await loadSnapshot();
    onChainUpdate();
  }

  async function handleDirectSync(): Promise<void> {
    if (data?.source === "notion_sync") {
      onShowError(
        "Acción no permitida",
        "El snapshot base ya fue generado por notion_sync y aún no se ha jugado una partida."
      );
      return;
    }

    isSyncing = true;
    try {
      const currentNames = (data?.players ?? []).map((p) => p.nombre);
      const response = await fetchNotionPlayers(currentNames);
      
      if (response.error) {
        onShowError("Error de Sincronización", response.error || "Error desconocido");
        isSyncing = false;
        return;
      }

      fetchedNotionPlayers = response.players;

      if (response.similar_names && response.similar_names.length > 0) {
        // Show resolution modal - isSyncing remains true until modal completes
        resolutionPairs = response.similar_names;
        resolutionVisible = true;
      } else {
        // No conflicts, merge directly - executeSyncMerge will handle isSyncing reset
        await executeSyncMerge([]);
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
      isSyncing = false;
    }
  }

  async function executeSyncMerge(merges: MergePair[]): Promise<void> {
    const mergeMap = new Map(merges.map((m) => [m.from, m]));
    const currentRows = data?.players ?? [];

    // Update existing players with Notion data (Strict Roster Rule: only update existing)
    const mergedPlayers = currentRows.map((row) => {
      const currentName = row.nombre;
      const mergeInfo = mergeMap.get(currentName);
      const notionName = mergeInfo ? mergeInfo.to : currentName;
      const normName = normalizeName(notionName);

      const notionPlayer = fetchedNotionPlayers.find(
        (p) => normalizeName(p.nombre) === normName || p.alias?.some((a: string) => normalizeName(a) === normName)
      );

      if (notionPlayer) {
        return {
          nombre: mergeInfo?.action === "merge_notion" ? notionPlayer.nombre : currentName,
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
      });

      if (result.error) {
        // Handle backend errors properly, including the Strict Guard message
        onShowError("Error de Sincronización", result.error);
        return;
      }

      // Only trigger updates if the sync was successful
      onChainUpdate();
      if (result.snapshot_id !== undefined) {
        setActiveNodeId(result.snapshot_id as number);
        onOpenSnapshot(result.snapshot_id);
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
    } finally {
      // Reset all sync-related state
      resolutionVisible = false;
      resolutionPairs = [];
      fetchedNotionPlayers = [];
      isSyncing = false;
    }
  }

  function handleResolutionComplete(merges: MergePair[]): void {
    void executeSyncMerge(merges);
  }

  function handleResolutionCancel(): void {
    resolutionVisible = false;
    resolutionPairs = [];
    fetchedNotionPlayers = [];
    isSyncing = false;
  }

  $effect(() => {
    void loadSnapshot();
  });
</script>

{#if loading}
  <p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>
{:else if data}
  {@const rows = data.players ?? []}
  <PanelLayout scrollable={false}>
    {#snippet header()}
      <div class="section" style="margin-bottom: 16px;">
        <div class="section-title">Snapshot #{id} · {sourceLabel(data?.source)}</div>
        <div class="node-meta" style="margin-bottom:8px">{esc(data?.created_at)}</div>
        <Button size="sm" variant={csvCopied ? 'success' : 'secondary'} icon={csvCopied ? "✅" : "📋"} fill={true} onclick={copyCsv}>{csvCopied ? "Copiado" : "Copiar tabla CSV"}</Button>
      </div>
      <div class="section-title" style="margin-bottom:6px">
        Jugadores <span
          style="color:var(--muted);font-weight:400;text-transform:none;font-size:11px"
          >— desactiva para excluir de la siguiente jornada</span
        >
      </div>
    {/snippet}

    {#snippet body()}
      <div class="table-wrap flex-table-wrap">
    <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th></th>
              <th>Exp.</th>
              <th>Juegos</th>
              <th>Prior.</th>
              <th>Desea</th>
              <th>GM</th>
            </tr>
          </thead>
          <tbody>
            {#each rows as r (r.nombre)}
              {@const nombre = esc(r.nombre)}
              {@const expColor =
                r.experiencia === "Nuevo" ? "#713f12" : "#166534"}
              {@const expBg =
                r.experiencia === "Nuevo" ? "#fef9c3" : "#f0fdf4"}
              <tr>
                <td><span class="player-name">{nombre}</span></td>
                <td style="padding-left: 0; width: 32px;">
                  <Button
                    variant="ghost"
                    size="sm"
                    iconOnly={true}
                    title="Renombrar"
                    onclick={() => handleRename(r.nombre)}
                    icon="✏️"
                  />
                </td>
                <td
                  ><span
                    style="font-size:10px;font-weight:700;color:{expColor};background:{expBg};padding:1px 6px;border-radius:4px"
                    >{esc(r.experiencia ?? "Nuevo")}</span
                  ></td
                >
                <td>{r.juegos_este_ano ?? 0}</td>
                <td>{r.prioridad === 1 ? "✓" : ""}</td>
                <td>{r.partidas_deseadas}</td>
                <td>{r.partidas_gm > 0 ? "✓" : ""}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/snippet}

    {#snippet footer()}
      <Button variant="secondary" fill={true} icon="📝" onclick={() => {
        const playersToEdit = (data?.players || []).map((p) => ({
          nombre: p.nombre,
          experiencia: p.experiencia ?? "Nuevo",
          juegos_este_ano: p.juegos_este_ano ?? 0,
          prioridad: p.prioridad ?? 0,
          partidas_deseadas: p.partidas_deseadas ?? 1,
          partidas_gm: p.partidas_gm ?? 0
        }));
        onEditDraft(id, 'manual', null, playersToEdit);
      }}>Editar</Button>
      <Button variant="secondary" fill={true} icon="🔄" onclick={handleDirectSync} disabled={isSyncing}>{isSyncing ? "Sincronizando..." : "Sincronizar Notion"}</Button>
      <Button variant="primary" fill={true} icon="▶️" onclick={handleOrganizar}>Organizar Partidas</Button>
    {/snippet}
  </PanelLayout>
{/if}

<SyncResolutionModal
  visible={resolutionVisible}
  pairs={resolutionPairs}
  onComplete={handleResolutionComplete}
  onCancel={handleResolutionCancel}
/>

<OrganizarConfirmModal
  visible={showConfirm}
  validation={validation}
  onConfirm={executeOrganizar}
  onEdit={() => {
    showConfirm = false;
    const playersToEdit = (data?.players || []).map((p) => ({
      nombre: p.nombre,
      experiencia: p.experiencia ?? "Nuevo",
      juegos_este_ano: p.juegos_este_ano ?? 0,
      prioridad: p.prioridad ?? 0,
      partidas_deseadas: p.partidas_deseadas ?? 1,
      partidas_gm: p.partidas_gm ?? 0
    }));
    onEditDraft(id, 'manual', null, playersToEdit);
  }}
  onCancel={() => {
    showConfirm = false;
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

  .player-name {
    white-space: nowrap;
  }
</style>
