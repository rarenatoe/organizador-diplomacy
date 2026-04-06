<script lang="ts">
  import type { SnapshotNode } from "../../types";
  import { fetchChain } from "../../api";
  import {
    setSnapshotCount,
    setChainData,
    getActiveNodeId,
  } from "../../stores.svelte";
  import GameNode from "./GameNode.svelte";
  import Button from "../ui/Button.svelte";

  interface Props {
    onOpenSnapshot: (id: number) => void;
    onOpenGame: (id: number) => void;
    onDeleteSnapshot: (id: number) => void;
    onDeleteGame: (id: number) => void;
    onNewDraft: (options?: { autoAction?: "notion" | "csv" }) => void;
    panelOpen?: boolean;
  }

  let {
    onOpenSnapshot,
    onOpenGame,
    onDeleteSnapshot,
    onDeleteGame,
    onNewDraft,
    panelOpen = false,
  }: Props = $props();

  let loading = $state(true);
  let localRoots = $state<SnapshotNode[]>([]);

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

{#snippet renderTree(nodes: SnapshotNode[])}
  {#each nodes as node (node.id)}
    <div class="chain-row">
      <div
        class="node node-snapshot group"
        class:active={getActiveNodeId() === node.id}
        data-id={node.id}
        onclick={() => handleSelect(node.id)}
        role="button"
        tabindex="0"
        onkeydown={(e) => e.key === "Enter" && handleSelect(node.id)}
      >
        <Button
          variant="ghost"
          destructive={true}
          size="xs"
          iconOnly={true}
          icon="🗑"
          class="absolute-top-right group-hover-reveal"
          title="Eliminar snapshot"
          onclick={(e) => {
            e.stopPropagation();
            handleDelete(node.id);
          }}
        />

        <div class="node-icon">📋</div>
        <div class="node-label">Snapshot #{node.id}</div>
        <div class="node-name">
          {(node.created_at || "").split(" ")[0] ?? ""}
        </div>
        <div class="node-meta">
          {(node.created_at || "").split(" ")[1] ?? ""}<br />
          {node.player_count} jugadores · {node.source}
        </div>

        <div class="node-badges">
          {#if node.is_latest}
            <span class="badge badge-latest">Actual</span>
          {/if}
        </div>
      </div>

      {#if node.branches && node.branches.length > 0}
        <div class="chain-fork">
          {#each node.branches as branch, i (branch.edge?.id ?? i)}
            {#if branch.output || (branch.edge && branch.edge.type === "game")}
              <div class="chain-branch">
                <span class="arrow">→</span>
                {#if branch.edge && branch.edge.type === "game"}
                  <GameNode
                    node={branch.edge}
                    onOpen={onOpenGame}
                    onDelete={onDeleteGame}
                  />
                  {#if branch.output}
                    <span class="arrow">→</span>
                  {/if}
                {/if}
                {#if branch.output}
                  {@render renderTree([branch.output])}
                {/if}
              </div>
            {/if}
          {/each}
        </div>
      {/if}
    </div>
  {/each}
{/snippet}

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
        <div
          style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;"
        >
          <Button
            variant="primary"
            icon="☁️"
            onclick={() => onNewDraft({ autoAction: "notion" })}
          >
            Importar de Notion
          </Button>
          <Button
            variant="secondary"
            icon="📥"
            onclick={() => onNewDraft({ autoAction: "csv" })}
          >
            Pegar CSV
          </Button>
          <Button variant="secondary" icon="📝" onclick={() => onNewDraft()}>
            Crear desde cero
          </Button>
        </div>
      </div>
    {:else}
      <div class="tree-container">
        {#each localRoots as root (root.id)}
          <div class="chain-lane" data-testid="chain-lane">
            {@render renderTree([root])}
          </div>
        {/each}
      </div>
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

  .tree-container {
    display: flex;
    flex-direction: column;
    gap: 32px;
    align-items: flex-start;
    padding: 16px 0;
  }
  .chain-row {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }
  .chain-fork {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .chain-branch {
    display: flex;
    align-items: center;
  }
  .arrow {
    color: var(--arrow-color);
    font-size: 18px;
    padding: 0 6px;
    flex-shrink: 0;
    user-select: none;
  }

  /* Node base styles */
  .node {
    cursor: pointer;
    border-radius: var(--radius);
    padding: 14px 16px;
    width: 180px;
    min-height: 160px;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    box-shadow: var(--shadow);
    transition:
      transform 0.15s,
      box-shadow 0.15s,
      border-color 0.15s;
    border: 2px solid transparent;
    user-select: none;
    position: relative;
  }
  .node:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  :global(.node.active) {
    box-shadow: 0 0 0 3px var(--active-glow);
    z-index: 45;
  }

  /* Snapshot node styling */
  .node-snapshot {
    background: var(--csv-bg);
    border-color: var(--csv-border);
  }
  :global(.node.active.node-snapshot) {
    border-color: var(--csv-border);
  }

  /* Node children styling */
  .node-icon {
    font-size: 20px;
    margin-bottom: 5px;
  }
  .node-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--muted);
    margin-bottom: 3px;
  }
  .node-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    word-break: break-all;
    line-height: 1.4;
  }
  .node-meta {
    font-size: 11px;
    color: var(--muted);
    margin-top: 6px;
    line-height: 1.6;
  }

  /* Badges */
  .node-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: auto;
    min-height: 18px;
  }
  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 99px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-top: 5px;
  }
  .badge-latest {
    background: var(--badge-latest-bg);
    color: var(--badge-latest-text);
    border: 1px solid var(--badge-latest-border);
  }
</style>
