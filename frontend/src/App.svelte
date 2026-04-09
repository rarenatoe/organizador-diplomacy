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
  import TerminalModal from "./components/modals/TerminalModal.svelte";
  import "../static/style.css";

  // Component refs
  let chainViewer = $state<ChainViewer | null>(null);
  // @ts-ignore: Component reference needed for exported toast functions
  let toaster = $state<Toaster | null>(null);

  // Modal state
  let modalVisible = $state(false);
  let modalTitle = $state("");
  let modalOutput = $state("");
  let modalIsError = $state(false);
  let modalLoading = $state(false);

  function showError(title: string, output: string): void {
    modalTitle = title;
    modalOutput = output;
    modalIsError = true;
    modalLoading = false;
    modalVisible = true;
  }

  function openSnapshot(id: number): void {
    nav.clearAndPush({ title: `Snapshot #${id}`, type: "snapshot", id });
  }

  function openGame(id: number): void {
    nav.clearAndPush({ title: "Jornada", type: "game", id });
  }

  function openGameDraft(
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
        draftKey: Date.now(), // Simple way to force re-renders if needed
      },
    });
  }

  function openDraft(
    parentId: number | null = null,
    eventType: "sync" | "manual" | "edit" = "manual",
    autoAction: "notion" | "csv" | null = null,
    players: EditPlayerRow[] = [],
  ): void {
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

    // If there is no parent, it's a brand new root-level flow. Reset the stack.
    if (parentId === null) {
      nav.clearAndPush(panelConfig);
    } else {
      // Otherwise, we are drilling down from an existing snapshot.
      nav.push(panelConfig);
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
      nav.close();
      await chainViewer?.loadChain();
    } catch (e) {
      alert(`Error de conexión: ${String(e)}`);
    }
  }

  // Delete game
  async function handleDeleteGame(id: number): Promise<void> {
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
    onDeleteSnapshot={handleDeleteSnapshot}
    onDeleteGame={handleDeleteGame}
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
        onChainUpdate={handleChainUpdate}
        onOpenSnapshot={openSnapshot}
        onOpenGame={openGame}
        onOpenGameDraft={openGameDraft}
        onEditDraft={(parentId, eventType, autoAction, players) =>
          openDraft(parentId, eventType, autoAction ?? null, players ?? [])}
        onShowError={showError}
        onShowToast={(message) => toaster?.showSuccessToast(message)}
      />
    {:else if nav.current?.type === "draft"}
      {#key nav.current.draftProps?.draftKey}
        <SnapshotDraft
          parentId={nav.current.draftProps?.parentId ?? null}
          initialPlayers={nav.current.draftProps?.initialPlayers ?? []}
          defaultEventType={nav.current.draftProps?.eventType ?? "manual"}
          autoAction={nav.current.draftProps?.autoAction ?? null}
          onClose={nav.close}
          onCancel={nav.pop}
          onChainUpdate={handleChainUpdate}
          onOpenSnapshot={openSnapshot}
          onShowError={showError}
        />
      {/key}
    {:else if nav.current?.type === "game" && nav.current.id !== null}
      <GameDetail id={nav.current.id} {openGameDraft} />
    {:else if nav.current?.type === "game_draft" && nav.current.id !== null}
      <GameDraft
        snapshotId={nav.current.draftProps?.parentId ?? 0}
        onClose={nav.close}
        onCancel={nav.pop}
        onChainUpdate={handleChainUpdate}
        onOpenGame={openGame}
        onShowError={showError}
        editingGameId={nav.current.draftProps?.editingGameId ?? null}
        initialDraft={nav.current.draftProps?.initialData ?? null}
      />
    {:else if nav.current?.type === "sync" && nav.current.id !== null}
      <SyncDetail id={nav.current.id} />
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
