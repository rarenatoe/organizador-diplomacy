<script lang="ts">
  import type { RunResult, EditPlayerRow } from "./types";
  import { runScript, deleteSnapshot as apiDeleteSnapshot } from "./api";
  import { setActiveNodeId } from "./stores.svelte";
  import { findLatestSnapshotId, findLatestGameId } from "./snapshotUtils";
  import Header from "./components/Header.svelte";
  import ChainViewer from "./components/ChainViewer.svelte";
  import SidePanel from "./components/SidePanel.svelte";
  import SnapshotDetail from "./components/SnapshotDetail.svelte";
  import SnapshotDraft from "./components/SnapshotDraft.svelte";
  import GameDraft from "./components/GameDraft.svelte";
  import GameDetail from "./components/GameDetail.svelte";
  import SyncDetail from "./components/SyncDetail.svelte";
  import Toaster from "./components/Toaster.svelte";
  import TerminalModal from "./components/TerminalModal.svelte";
  import "../static/style.css";

  // Component refs
  let chainViewer = $state<ChainViewer | null>(null);
  let toaster = $state<Toaster | null>(null);

  // Panel state
  let panelOpen = $state(false);
  let panelTitle = $state("");
  let panelType = $state<"snapshot" | "game" | "sync" | "draft" | "game_draft" | null>(null);
  let panelId = $state<number | null>(null);

  // Draft state
  let draftParentId = $state<number | null>(null);
  let draftEventType = $state<"sync" | "manual" | "edit">("manual");
  let draftAutoAction = $state<'notion' | 'csv' | null>(null);
  let draftInitialPlayers = $state<EditPlayerRow[]>([]);

  // Modal state
  let modalVisible = $state(false);
  let modalTitle = $state("");
  let modalOutput = $state("");
  let modalIsError = $state(false);
  let modalLoading = $state(false);

  // Syncing/running state
  let syncing = $state(false);
  let running = $state(false);

  const SCRIPT_LABELS: Record<string, string> = {
    notion_sync: "↻ Sync Notion",
    organizar: "▶ Organizar",
  };


  // Panel handlers
  function openPanel(title: string, type: typeof panelType, id: number): void {
    panelTitle = title;
    panelType = type;
    panelId = id;
    panelOpen = true;
  }

  function closePanel(): void {
    panelOpen = false;
    panelType = null;
    panelId = null;
    setActiveNodeId(null);
  }

  function openSnapshot(id: number): void {
    openPanel(`Snapshot #${id}`, "snapshot", id);
    setActiveNodeId(id);
  }

  function openGame(id: number): void {
    openPanel("Jornada", "game", id);
    setActiveNodeId(id);
  }

  function openSync(id: number): void {
    openPanel("Sync Notion", "sync", id);
    setActiveNodeId(id);
  }

  function openGameDraft(snapshotId: number): void {
    openPanel(`Draft - Snapshot #${snapshotId}`, "game_draft", snapshotId);
    setActiveNodeId(snapshotId);
  }

  function openDraft(parentId: number | null = null, eventType: string = "manual", autoAction: 'notion' | 'csv' | null = null, players: EditPlayerRow[] = []): void {
    closePanel();
    draftParentId = parentId;
    draftEventType = eventType as "sync" | "manual" | "edit";
    draftAutoAction = autoAction;
    draftInitialPlayers = players;
    panelType = "draft";
    panelOpen = true;
    panelTitle = parentId === null ? "Nueva Lista" : (eventType === 'sync' ? `Sincronizando #${parentId}` : `Editando #${parentId}`);
    if (parentId !== null) {
      setActiveNodeId(parentId);
    }
  }

  // Script execution
  async function handleRunScript(script: string): Promise<void> {
    const label = SCRIPT_LABELS[script] ?? script;
    modalTitle = `Ejecutando ${label}…`;
    modalOutput = "";
    modalIsError = false;
    modalLoading = true;
    modalVisible = true;
    running = true;

    try {
      const data = await runScript(script, null);
      const ok = data.returncode === 0;

      if (ok && script === "organizar") {
        modalVisible = false;
        toaster?.showSuccessToast("Organizar completado");
        await chainViewer?.loadChain();

        // Find and open the latest game
        const { fetchChain } = await import("./api");
        const chainData = await fetchChain();
        const gameId = findLatestGameId(chainData.roots);
        if (gameId !== null) {
          setActiveNodeId(gameId);
          openGame(gameId);
        }
      } else if (ok) {
        modalTitle = `${label} completado`;
        modalOutput =
          (data.stdout ?? "") +
          (data.stderr ? "\n[stderr]\n" + data.stderr : "");
        await chainViewer?.loadChain();
      } else {
        modalTitle = `Error en ${label}`;
        modalOutput =
          (data.stdout ?? "") +
          (data.stderr ? "\n[stderr]\n" + data.stderr : "");
        modalIsError = true;
      }
    } catch (e) {
      modalTitle = "Error de conexión";
      modalOutput = String(e);
      modalIsError = true;
    } finally {
      modalLoading = false;
      running = false;
    }
  }

  // Delete snapshot
  async function handleDeleteSnapshot(id: number): Promise<void> {
    if (
      !confirm(
        `¿Eliminar snapshot #${id} y todos sus descendientes?\nEsta acción no se puede deshacer.`,
      )
    )
      return;
    try {
      const data = await apiDeleteSnapshot(id);
      if (data.error) {
        alert(`Error al eliminar: ${data.error}`);
        return;
      }
      closePanel();
      await chainViewer?.loadChain();
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    }
  }

  function handleChainUpdate(): void {
    void chainViewer?.loadChain();
  }
</script>

<Header
  onNewDraft={() => openDraft()}
/>

<div class="main">
  <ChainViewer
    bind:this={chainViewer}
    onOpenSnapshot={openSnapshot}
    onOpenGame={openGame}
    onOpenSync={openSync}
    onDeleteSnapshot={handleDeleteSnapshot}
    onNewDraft={(options) => openDraft(null, "manual", options?.autoAction ?? null)}
    panelOpen={panelOpen}
  />
  <SidePanel title={panelTitle} open={panelOpen} onClose={closePanel}>
    {#if panelType === "snapshot" && panelId !== null}
      <SnapshotDetail
        id={panelId}
        onClose={closePanel}
        onChainUpdate={handleChainUpdate}
        onOpenSnapshot={openSnapshot}
        onOpenGame={openGame}
        onOpenGameDraft={openGameDraft}
        onEditDraft={(parentId: number, eventType: string, autoAction?: 'notion' | 'csv' | null, players?: EditPlayerRow[]) => openDraft(parentId, eventType, autoAction ?? null, players ?? [])}
        onShowError={(title, output) => { modalTitle = title; modalOutput = output; modalIsError = true; modalLoading = false; modalVisible = true; }}
      />
    {:else if panelType === "draft"}
      <SnapshotDraft
        parentId={draftParentId}
        initialPlayers={draftInitialPlayers}
        defaultEventType={draftEventType}
        autoAction={draftAutoAction}
        onClose={closePanel}
        onChainUpdate={handleChainUpdate}
        onOpenSnapshot={openSnapshot}
        onShowError={(title, output) => { modalTitle = title; modalOutput = output; modalIsError = true; modalLoading = false; modalVisible = true; }}
      />
    {:else if panelType === "game" && panelId !== null}
      <GameDetail id={panelId} />
    {:else if panelType === "game_draft" && panelId !== null}
      <GameDraft
        snapshotId={panelId}
        onClose={closePanel}
        onChainUpdate={handleChainUpdate}
        onOpenGame={openGame}
        onShowError={(title, output) => { modalTitle = title; modalOutput = output; modalIsError = true; modalLoading = false; modalVisible = true; }}
      />
    {:else if panelType === "sync" && panelId !== null}
      <SyncDetail id={panelId} />
    {/if}
  </SidePanel>
</div>

<Toaster bind:this={toaster} />

<TerminalModal
  visible={modalVisible}
  title={modalTitle}
  output={modalOutput}
  isError={modalIsError}
  loading={modalLoading}
  onClose={() => (modalVisible = false)}
/>

<style>
  .main {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
  }
</style>
