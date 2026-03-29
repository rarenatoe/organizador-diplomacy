<script lang="ts">
  import type { EditPlayerRow, DraftResponse } from "./types";
  import { deleteSnapshot as apiDeleteSnapshot } from "./api";
  import { setActiveNodeId } from "./stores.svelte";
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
  // @ts-ignore: Component reference needed for exported toast functions
  let toaster = $state<Toaster | null>(null);

  // Panel state
  let panelOpen = $state(false);
  let panelTitle = $state("");
  let panelType = $state<
    "snapshot" | "game" | "sync" | "draft" | "game_draft" | null
  >(null);
  let panelId = $state<number | null>(null);

  // Draft state
  let draftParentId = $state<number | null>(null);
  let draftEventType = $state<"sync" | "manual" | "edit">("manual");
  let draftAutoAction = $state<"notion" | "csv" | null>(null);
  let draftInitialPlayers = $state<EditPlayerRow[]>([]);
  let draftInitialData = $state<DraftResponse | null>(null);
  let draftEditingGameId = $state<number | null>(null);

  // Modal state
  let modalVisible = $state(false);
  let modalTitle = $state("");
  let modalOutput = $state("");
  let modalIsError = $state(false);
  let modalLoading = $state(false);

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

  function openGameDraft(
    snapshotId: number,
    initialData?: DraftResponse,
    editingGameId?: number,
  ): void {
    closePanel();
    draftParentId = snapshotId;
    draftEventType = "edit";
    draftAutoAction = null;
    draftInitialPlayers = [];
    draftInitialData = initialData ?? null;
    draftEditingGameId = editingGameId ?? null;
    panelType = "game_draft";
    panelOpen = true;
    panelTitle = editingGameId
      ? `Editando Jornada #${editingGameId}`
      : `Draft - Snapshot #${snapshotId}`;
    panelId = snapshotId;
    setActiveNodeId(editingGameId || snapshotId);
  }

  function openDraft(
    parentId: number | null = null,
    eventType: "sync" | "manual" | "edit" = "manual",
    autoAction: "notion" | "csv" | null = null,
    players: EditPlayerRow[] = [],
  ): void {
    closePanel();
    draftParentId = parentId;
    draftEventType = eventType;
    draftAutoAction = autoAction;
    draftInitialPlayers = players;
    panelType = "draft";
    panelOpen = true;
    panelTitle =
      parentId === null
        ? "Nueva Lista"
        : eventType === "sync"
          ? `Sincronizando #${parentId}`
          : `Editando #${parentId}`;
    if (parentId !== null) {
      setActiveNodeId(parentId);
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

<Header onNewDraft={() => openDraft()} />

<div class="main">
  <ChainViewer
    bind:this={chainViewer}
    onOpenSnapshot={openSnapshot}
    onOpenGame={openGame}
    onOpenSync={openSync}
    onDeleteSnapshot={handleDeleteSnapshot}
    onNewDraft={(options) =>
      openDraft(null, "manual", options?.autoAction ?? null)}
    {panelOpen}
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
        onEditDraft={(
          parentId: number,
          eventType: "sync" | "manual" | "edit",
          autoAction?: "notion" | "csv" | null,
          players?: EditPlayerRow[],
        ) => openDraft(parentId, eventType, autoAction ?? null, players ?? [])}
        onShowError={(title, output) => {
          modalTitle = title;
          modalOutput = output;
          modalIsError = true;
          modalLoading = false;
          modalVisible = true;
        }}
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
        onShowError={(title, output) => {
          modalTitle = title;
          modalOutput = output;
          modalIsError = true;
          modalLoading = false;
          modalVisible = true;
        }}
      />
    {:else if panelType === "game" && panelId !== null}
      <GameDetail id={panelId} {openGameDraft} />
    {:else if panelType === "game_draft" && panelId !== null}
      <GameDraft
        snapshotId={panelId}
        onClose={closePanel}
        onChainUpdate={handleChainUpdate}
        onOpenGame={openGame}
        onShowError={(title, output) => {
          modalTitle = title;
          modalOutput = output;
          modalIsError = true;
          modalLoading = false;
          modalVisible = true;
        }}
        editingGameId={draftEditingGameId}
        initialDraft={draftInitialData}
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
