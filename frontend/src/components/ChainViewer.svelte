<script lang="ts">
  import type { SnapshotNode } from "../types";
  import { fetchChain } from "../api";
  import {
    setSnapshotCount,
    setChainData,
  } from "../stores.svelte";
  import SnapshotGroupNode from "./SnapshotGroupNode.svelte";
  import { groupSnapshots } from "../groupSnapshots";

  interface Props {
    onOpenSnapshot: (id: number) => void;
    onOpenGame: (id: number) => void;
    onOpenSync: (id: number) => void;
    onDeleteSnapshot: (id: number) => void;
    onNewDraft: (options?: { autoAction?: 'notion' | 'csv' }) => void;
    panelOpen?: boolean;
  }

  let { onOpenSnapshot, onOpenGame, onOpenSync, onDeleteSnapshot, onNewDraft, panelOpen = false }: Props =
    $props();

  let loading = $state(true);
  let localRoots = $state<SnapshotNode[]>([]);

  // Now this correctly tracks changes because localRoots is a $state rune
  let groupedRoots = $derived(groupSnapshots(localRoots));

  export async function loadChain(): Promise<void> {
    loading = true;
    try {
      const data = await fetchChain();
      setChainData(data);
      setSnapshotCount(data.roots?.length ?? 0);
      localRoots = data.roots ?? [];
    } finally {
      loading = false;
    }
  }

  function handleSelect(id: number): void {
    onOpenSnapshot(id);
  }

  function handleDelete(id: number): void {
    onDeleteSnapshot(id);
  }

  // Load chain on mount
  $effect(() => {
    void loadChain();
  });
</script>

<div class="chain-area">
  <div id="chain" class:panel-open={panelOpen}>
    {#if loading}
      <div class="empty-state">
        <div class="icon">⏳</div>
        <p>Cargando...</p>
      </div>
    {:else if !localRoots.length}
      <div class="empty-state">
        <div class="icon">📂</div>
        <p>No hay snapshots en la DB.</p>
        <p>Comienza importando jugadores o creando una versión desde cero.</p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;">
          <button class="btn btn-primary" onclick={() => onNewDraft({ autoAction: 'notion' })}>
            ☁️ Importar de Notion
          </button>
          <button class="btn btn-secondary" onclick={() => onNewDraft({ autoAction: 'csv' })}>
            📥 Pegar CSV
          </button>
          <button class="btn btn-secondary" onclick={() => onNewDraft()}>
            📝 Crear desde cero
          </button>
        </div>
      </div>
    {:else}
      {#each groupedRoots as group (group.versions[0]!.snapshot.id)}
        <SnapshotGroupNode
          {group}
          onSelect={handleSelect}
          onDelete={handleDelete}
          onOpenGame={onOpenGame}
          onOpenSync={onOpenSync}
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

  :global(#chain.panel-open .node:not(.active)) {
    opacity: 0.4;
    filter: grayscale(60%);
    box-shadow: none;
  }
</style>
