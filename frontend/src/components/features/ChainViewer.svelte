<script lang="ts">
  import { apiChain, type SnapshotNode } from "../../generated-api";
  import { formatDate } from "../../i18n";
  import {
    getActiveNodeId,
    setChainData,
    setSnapshotCount,
  } from "../../stores.svelte";
  import Button from "../ui/Button.svelte";
  import Node from "../ui/Node.svelte";

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
      const { data } = await apiChain();
      setChainData(data);
      setSnapshotCount(data?.roots.length ?? 0);
      localRoots = data?.roots ?? [];
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
      <Node
        variant="snapshot"
        isActive={getActiveNodeId() === node.id}
        title={`Snapshot #${node.id}`}
        subtitle={formatDate(node.created_at)}
        icon="📋"
        metadata={[`${node.player_count} jugadores`, node.source]}
        onDelete={() => handleDelete(node.id)}
        onClick={() => handleSelect(node.id)}
      />

      {#if node.branches && node.branches.length > 0}
        <div class="chain-fork">
          {#each node.branches as branch, i (branch.edge?.id ?? i)}
            {#if branch.output || (branch.edge && branch.edge.type === "game")}
              <div class="chain-branch">
                <span class="arrow">→</span>
                {#if branch.edge && branch.edge.type === "game"}
                  <Node
                    variant="game"
                    isActive={getActiveNodeId() === branch.edge.id}
                    title="Jornada"
                    subtitle={formatDate(branch.edge.created_at)}
                    icon="📊"
                    metadata={[
                      `${branch.edge.mesa_count} partida(s)`,
                      `${branch.edge.espera_count} en espera`,
                    ]}
                    onDelete={onDeleteGame
                      ? () => onDeleteGame(branch.edge.id)
                      : undefined}
                    onClick={() => onOpenGame(branch.edge.id)}
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
        <div class="action-row">
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
    padding: var(--space-40) var(--space-32);
    display: flex;
    align-items: flex-start;
  }

  #chain {
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
    min-height: calc(var(--space-8) * 17);
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-16);
    padding: var(--space-56);
    color: var(--text-muted);
    text-align: center;
  }

  .action-row {
    display: flex;
    gap: var(--space-8);
    flex-wrap: wrap;
    justify-content: center;
  }

  .empty-state .icon {
    font-size: var(--space-40);
  }

  .empty-state p {
    font-size: 13px;
  }

  :global(#chain.panel-open .node:not(.active)) {
    opacity: 0.6;
    filter: grayscale(60%);
    box-shadow: none;
  }

  .tree-container {
    display: flex;
    flex-direction: column;
    gap: var(--space-32);
    align-items: flex-start;
    padding: var(--space-16) 0;
  }
  .chain-row {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }
  .chain-fork {
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
  }
  .chain-branch {
    display: flex;
    align-items: center;
  }
  .arrow {
    color: var(--arrow-color);
    font-size: var(--space-16);
    padding: 0 var(--space-8);
    flex-shrink: 0;
    user-select: none;
  }
</style>
