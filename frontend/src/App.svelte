<script lang="ts">
  import ChainViewer from "./components/features/ChainViewer.svelte";
  import GameDetail from "./components/features/GameDetail.svelte";
  import GameDraft from "./components/features/GameDraft.svelte";
  import SnapshotDetail from "./components/features/SnapshotDetail.svelte";
  import SnapshotDraft from "./components/features/SnapshotDraft.svelte";
  import SyncDetail from "./components/features/SyncDetail.svelte";
  import Toaster from "./components/features/Toaster.svelte";
  import Header from "./components/layout/Header.svelte";
  import SidePanel from "./components/layout/SidePanel.svelte";
  import TerminalModal, {
    type TerminalState,
  } from "./components/modals/TerminalModal.svelte";
  import {
    apiGameDelete,
    apiSyncStatus,
    type GameDraftResponseOutput,
  } from "./generated-api";
  import { nav, type PanelContext } from "./navigation.svelte";
  import type { EditPlayerRow } from "./types";

  import "../static/style.css";

  import { apiSnapshot, type SnapshotSaveEventType } from "./generated-api";

  let isAppReady = $state(false);
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
    initialData?: GameDraftResponseOutput,
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
        saveEventType: "manual",
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
    saveEventType: SnapshotSaveEventType = "manual",
    autoAction: "notion" | "csv" | null = null,
    players: EditPlayerRow[] = [],
  ): void {
    // 2. Simplified Title Resolution
    let title: string;
    if (parentId === null) {
      title = "Nueva Lista";
    } else if (saveEventType === "sync") {
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
        saveEventType,
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
      const data = await apiSnapshot({
        method: "DELETE",
        path: { snapshot_id: id },
      });
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
      await apiGameDelete({ path: { game_id: id } });
      nav.close();
      await chainViewer?.loadChain();
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    }
  }

  function onChainUpdate(): void {
    void chainViewer?.loadChain();
  }

  async function checkInitialSync() {
    try {
      const { data } = await apiSyncStatus();
      if (data) {
        // If it's done, errored, or no token is provided, let the user in
        if (["ready", "unconfigured", "error"].includes(data.status)) {
          isAppReady = true;
          return;
        }
      }
    } catch (e) {
      // Fallback: if the endpoint fails, let them in to avoid an infinite loader
      isAppReady = true;
      return;
    }

    // If still "pending" or "syncing", poll again in 1 second
    setTimeout(checkInitialSync, 1000);
  }

  $effect(() => {
    checkInitialSync();
  });
</script>

{#if !isAppReady}
  <div class="app-loading-screen">
    <div class="spinner"></div>
    <h2>Iniciando Organizador...</h2>
    <p>Sincronizando caché con Notion</p>
  </div>
{:else}
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
            saveEventType={nav.current.draftProps.saveEventType}
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
{/if}

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

  .app-loading-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: var(--bg-primary);
    color: var(--text-primary);
    gap: var(--space-16);
  }

  .app-loading-screen .spinner {
    width: var(--space-40);
    height: var(--space-40);
    border: 3px solid var(--border-subtle);
    border-top-color: var(--primary-bg);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
</style>
