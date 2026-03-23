<script lang="ts">
  import type { RunResult, SyncDetectResult, MergePair } from "./types";
  import { runScript, detectSync, confirmSync, deleteSnapshot as apiDeleteSnapshot } from "./api";
  import { getSelectedSnapshot, setSelectedSnapshot, setActiveNodeId, deselectSnapshot } from "./stores.svelte";
  import { findLatestSnapshotId, findLatestGameId } from "./snapshotUtils";
  import Header from "./components/Header.svelte";
  import ChainViewer from "./components/ChainViewer.svelte";
  import SidePanel from "./components/SidePanel.svelte";
  import SnapshotDetail from "./components/SnapshotDetail.svelte";
  import GameDetail from "./components/GameDetail.svelte";
  import SyncDetail from "./components/SyncDetail.svelte";
  import Toaster from "./components/Toaster.svelte";
  import SyncResolutionModal from "./components/SyncResolutionModal.svelte";
  import TerminalModal from "./components/TerminalModal.svelte";
  import "../static/style.css";

  // Component refs
  let chainViewer = $state<ChainViewer | null>(null);
  let toaster = $state<Toaster | null>(null);

  // Panel state
  let panelOpen = $state(false);
  let panelTitle = $state("");
  let panelType = $state<"snapshot" | "game" | "sync" | null>(null);
  let panelId = $state<number | null>(null);

  // Modal state
  let modalVisible = $state(false);
  let modalTitle = $state("");
  let modalOutput = $state("");
  let modalIsError = $state(false);
  let modalLoading = $state(false);

  // Resolution modal state
  let resolutionVisible = $state(false);
  let resolutionPairs = $state<SyncDetectResult["similar_names"]>([]);

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
  }

  function openGame(id: number): void {
    openPanel("Jornada", "game", id);
  }

  function openSync(id: number): void {
    openPanel("Sync Notion", "sync", id);
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
      const data = await runScript(script, getSelectedSnapshot());
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
          setActiveNodeId(String(gameId));
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

  // Sync flow
  async function handleSync(): Promise<void> {
    syncing = true;
    const toastId = toaster?.showSyncingToast() ?? "";

    try {
      const detectData = await detectSync(getSelectedSnapshot());

      if (detectData.similar_names.length === 0) {
        await handleSyncConfirm([], toastId);
      } else {
        toaster?.dismissAll();
        resolutionPairs = detectData.similar_names;
        resolutionVisible = true;
      }
    } catch (e) {
      toaster?.dismissAll();
      toaster?.showErrorToast(`Error de conexión: ${String(e)}`);
    } finally {
      syncing = false;
    }
  }

  async function handleSyncConfirm(
    merges: MergePair[],
    toastId?: string,
  ): Promise<void> {
    const tid = toastId ?? (toaster?.showSyncingToast() ?? "");
    syncing = true;

    try {
      const data = await confirmSync(getSelectedSnapshot(), merges);
      const ok = data.returncode === 0;
      toaster?.dismissAll();
      if (ok) {
        toaster?.showSuccessToast("Sync Notion completado");
        await chainViewer?.loadChain();

        // Find and open the newly synced snapshot
        const { fetchChain } = await import("./api");
        const chainData = await fetchChain();
        const snapId = findLatestSnapshotId(chainData.roots);
        if (snapId !== null) {
          setSelectedSnapshot(snapId);
          setActiveNodeId(String(snapId));
          openSnapshot(snapId);
        }
      } else {
        toaster?.showErrorToast(
          `Error en Sync Notion: ${data.stderr ?? "desconocido"}`,
        );
      }
    } catch (e) {
      toaster?.dismissAll();
      toaster?.showErrorToast(`Error de conexión: ${String(e)}`);
    } finally {
      syncing = false;
    }
  }

  function handleResolutionComplete(merges: MergePair[]): void {
    resolutionVisible = false;
    void handleSyncConfirm(merges);
  }

  function handleResolutionCancel(): void {
    resolutionVisible = false;
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
      const selected = getSelectedSnapshot();
      if (selected !== null && data.deleted.includes(selected)) {
        deselectSnapshot();
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
  onrefresh={() => chainViewer?.loadChain()}
  onsync={handleSync}
  onorganizar={() => handleRunScript("organizar")}
  {syncing}
  {running}
/>

<div class="main">
  <ChainViewer
    bind:this={chainViewer}
    onopenSnapshot={openSnapshot}
    onopenGame={openGame}
    onopenSync={openSync}
    ondeleteSnapshot={handleDeleteSnapshot}
  />
  <SidePanel title={panelTitle} open={panelOpen} onclose={closePanel}>
    {#if panelType === "snapshot" && panelId !== null}
      <SnapshotDetail
        id={panelId}
        onclose={closePanel}
        onchainUpdate={handleChainUpdate}
        onopenSnapshot={openSnapshot}
      />
    {:else if panelType === "game" && panelId !== null}
      <GameDetail id={panelId} />
    {:else if panelType === "sync" && panelId !== null}
      <SyncDetail id={panelId} />
    {/if}
  </SidePanel>
</div>

<Toaster bind:this={toaster} />

<SyncResolutionModal
  visible={resolutionVisible}
  pairs={resolutionPairs}
  oncomplete={handleResolutionComplete}
  oncancel={handleResolutionCancel}
/>

<TerminalModal
  visible={modalVisible}
  title={modalTitle}
  output={modalOutput}
  isError={modalIsError}
  loading={modalLoading}
  onclose={() => (modalVisible = false)}
/>