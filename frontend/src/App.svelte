<script lang="ts">
  import type { EditPlayerRow, DraftResponse } from "./types";
  import { deleteSnapshot as apiDeleteSnapshot, deleteGame } from "./api";
  import { setActiveNodeId } from "./stores.svelte";
  import { nav, type PanelContext } from "./navigation.svelte";
  import Header from "./components/layout/Header.svelte";
  import ChainViewer from "./components/features/ChainViewer.svelte";
  import SidePanel from "./components/layout/SidePanel.svelte";
  import SnapshotDetail from "./components/features/SnapshotDetail.svelte";
  import SnapshotDraft from "./components/features/SnapshotDraft.svelte";
  import GameDraft from "./components/features/GameDraft.svelte";
  import GameDetail from "./components/features/GameDetail.svelte";
  import SyncDetail from "./components/features/SyncDetail.svelte";
  import Toaster from "./components/features/Toaster.svelte";
  import TerminalModal, {
    type TerminalState,
  } from "./components/modals/TerminalModal.svelte";
  import "../static/style.css";

  let chainViewer = $state<ChainViewer | null>(null);
  let toaster = $state<Toaster | null>(null);

  // 1. Unified State Machine instead of 5 isolated flags
  let terminalState = $state<TerminalState>({ status: "hidden" });

  function showError(title: string, output: string): void {
    terminalState = { status: "error", title, output };
  }

  function onOpenSnapshot(id: number): void {
    nav.clearAndPush({ title: `Snapshot #${id}`, type: "snapshot", id });
  }

  function onOpenGame(id: number): void {
    nav.clearAndPush({ title: "Jornada", type: "game", id });
  }

  function onOpenGameDraft(
    snapshotId: number,
    initialData?: DraftResponse,
    editingGameId?: number,
  ): void {
    nav.push({
      title: editingGameId
        ? `Editando Jornada #${editingGameId}`
        : `Draft - Snapshot #${snapshotId}`,
      type: "game_draft",
      id: editingGameId ?? snapshotId,
      draftProps: {
        parentId: snapshotId,
        eventType: "edit",
        autoAction: null,
        initialPlayers: [],
        initialData: initialData ?? null,
        editingGameId: editingGameId ?? null,
        draftKey: Date.now(),
      },
    });
  }

  function openDraft(
    parentId: number | null = null,
    eventType: "sync" | "manual" | "edit" = "manual",
    autoAction: "notion" | "csv" | null = null,
    players: EditPlayerRow[] = [],
  ): void {
    // 2. Simplified Title Resolution
    let title: string;
    if (parentId === null) {
      title = "Nueva Lista";
    } else if (eventType === "sync") {
      title = `Sincronizando #${parentId}`;
    } else {
      title = `Editando #${parentId}`;
    }

    const panelConfig: PanelContext = {
      title,
      type: "draft",
      id: parentId,
      draftProps: {
        parentId,
        eventType,
        autoAction,
        initialPlayers: players,
        initialData: null,
        editingGameId: null,
        draftKey: Date.now(),
      },
    };

    if (parentId === null) nav.clearAndPush(panelConfig);
    else nav.push(panelConfig);
  }

  async function onDeleteSnapshot(id: number): Promise<void> {
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
      nav.close();
      await chainViewer?.loadChain();
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    }
  }

  async function onDeleteGame(id: number): Promise<void> {
    if (
      !confirm(`¿Eliminar jornada #${id}?\nEsta acción no se puede deshacer.`)
    )
      return;
    try {
      await deleteGame(id);
      nav.close();
      await chainViewer?.loadChain();
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    }
  }

  function onChainUpdate(): void {
    void chainViewer?.loadChain();
  }
</script>

<Header onNewDraft={() => openDraft()} />

<div class="main">
  <ChainViewer
    bind:this={chainViewer}
    {onOpenSnapshot}
    {onOpenGame}
    {onDeleteSnapshot}
    {onDeleteGame}
    onNewDraft={(options) =>
      openDraft(null, "manual", options?.autoAction ?? null)}
    panelOpen={nav.isOpen}
  />
  <SidePanel
    title={nav.current?.title ?? ""}
    open={nav.isOpen}
    onClose={nav.close}
  >
    {#if nav.current?.type === "snapshot" && nav.current.id !== null}
      <SnapshotDetail
        id={nav.current.id}
        onClose={nav.close}
        {onChainUpdate}
        {onOpenSnapshot}
        {onOpenGame}
        {onOpenGameDraft}
        onEditDraft={(parentId, eventType, autoAction, players) =>
          openDraft(parentId, eventType, autoAction ?? null, players ?? [])}
        onShowError={showError}
        onShowToast={(message) => toaster?.showSuccessToast(message)}
      />
    {:else if nav.current?.type === "draft" && nav.current.draftProps}
      {#key nav.current.draftProps.draftKey}
        <SnapshotDraft
          parentId={nav.current.draftProps.parentId}
          initialPlayers={nav.current.draftProps.initialPlayers}
          defaultEventType={nav.current.draftProps.eventType}
          autoAction={nav.current.draftProps.autoAction}
          onClose={nav.close}
          onCancel={nav.pop}
          {onChainUpdate}
          {onOpenSnapshot}
          onShowError={showError}
        />
      {/key}
    {:else if nav.current?.type === "game" && nav.current.id !== null}
      <GameDetail id={nav.current.id} {onOpenGameDraft} />
    {:else if nav.current?.type === "game_draft" && nav.current.draftProps && nav.current.id !== null}
      <GameDraft
        snapshotId={nav.current.draftProps.parentId ?? 0}
        onClose={nav.close}
        onCancel={nav.pop}
        {onChainUpdate}
        {onOpenGame}
        onShowError={showError}
        editingGameId={nav.current.draftProps.editingGameId}
        initialDraft={nav.current.draftProps.initialData}
      />
    {:else if nav.current?.type === "sync" && nav.current.id !== null}
      <SyncDetail id={nav.current.id} />
    {/if}
  </SidePanel>
</div>

<Toaster bind:this={toaster} />

<TerminalModal
  state={terminalState}
  onClose={() => (terminalState = { status: "hidden" })}
/>

<style>
  .main {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
  }
</style>
