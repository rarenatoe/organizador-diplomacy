<script lang="ts">
  import type { ChainData } from "../types";
  import { fetchChain } from "../api";
  import {
    setSnapshotCount,
    setChainData,
    getChainData,
    setActiveNodeId,
    setSelectedSnapshot,
  } from "../stores.svelte";
  import SnapshotNode from "./SnapshotNode.svelte";

  interface Props {
    onopenSnapshot: (id: number) => void;
    onopenGame: (id: number) => void;
    onopenSync: (id: number) => void;
    ondeleteSnapshot: (id: number) => void;
  }

  let { onopenSnapshot, onopenGame, onopenSync, ondeleteSnapshot }: Props =
    $props();

  let loading = $state(true);

  export async function loadChain(): Promise<void> {
    loading = true;
    try {
      const data = await fetchChain();
      setChainData(data);
      setSnapshotCount(data.roots?.length ?? 0);
    } finally {
      loading = false;
    }
  }

  function handleSelect(id: number): void {
    setActiveNodeId(String(id));
    setSelectedSnapshot(id);
    onopenSnapshot(id);
  }

  function handleDelete(id: number): void {
    ondeleteSnapshot(id);
  }

  // Load chain on mount
  $effect(() => {
    void loadChain();
  });
</script>

<div class="chain-area">
  <div id="chain">
    {#if loading}
      <div class="empty-state">
        <div class="icon">⏳</div>
        <p>Cargando...</p>
      </div>
    {:else if !getChainData()?.roots?.length}
      <div class="empty-state">
        <div class="icon">📂</div>
        <p>No hay snapshots en la DB.</p>
        <p>Ejecuta <em>Sync Notion</em> para comenzar.</p>
      </div>
    {:else}
      {#each getChainData()?.roots ?? [] as root (root.id)}
        <SnapshotNode
          node={root}
          onselect={handleSelect}
          ondelete={handleDelete}
          onopenGame={onopenGame}
          onopenSync={onopenSync}
        />
      {/each}
    {/if}
  </div>
</div>

<style>
  .chain-area {
    flex: 1;
    overflow-x: auto;
    overflow-y: auto;
    padding: 40px 36px;
    display: flex;
    align-items: flex-start;
  }

  #chain {
    display: flex;
    flex-direction: column;
    gap: 20px;
    min-height: 140px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 60px;
    color: var(--muted);
    text-align: center;
  }

  .empty-state .icon {
    font-size: 40px;
  }

  .empty-state p {
    font-size: 13px;
  }
</style>
