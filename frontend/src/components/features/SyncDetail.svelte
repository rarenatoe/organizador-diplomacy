<script lang="ts">
  import { apiChain, type SnapshotNode } from "../../generated-api";
  import PanelLayout from "../layout/PanelLayout.svelte";

  interface Props {
    id: number;
  }

  let { id }: Props = $props();

  let info = $state<{
    from_id: number;
    to_id: number | null;
    created_at: string;
  } | null>(null);
  let loading = $state(true);

  async function loadSyncInfo(): Promise<void> {
    loading = true;
    try {
      const { data } = await apiChain();
      function findSync(roots: SnapshotNode[]): void {
        for (const root of roots) {
          for (const branch of root.branches ?? []) {
            if (branch.edge.type === "sync" && branch.edge.id === id) {
              info = {
                from_id: branch.edge.from_id,
                to_id: branch.edge.to_id ?? null,
                created_at: branch.edge.created_at,
              };
            }
            if (branch.output) findSync([branch.output]);
          }
        }
      }
      if (data?.roots) findSync(data.roots);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void loadSyncInfo();
  });
</script>

{#if loading}
  <p class="loading-text">Cargando…</p>
{:else if info}
  <PanelLayout>
    {#snippet body()}
      <div class="section">
        <div class="section-title">Detalles del Sync</div>
        <div class="meta-grid">
          <span class="meta-key">Generado</span>
          <span class="meta-val">{info?.created_at}</span>
          <span class="meta-key">De snapshot</span>
          <span class="meta-val">#{info?.from_id}</span>
          <span class="meta-key">A snapshot</span>
          <span class="meta-val">#{info?.to_id}</span>
        </div>
      </div>
    {/snippet}
  </PanelLayout>
{:else}
  <PanelLayout>
    {#snippet body()}
      <p>Sync no encontrado.</p>
    {/snippet}
  </PanelLayout>
{/if}

<style>
  .loading-text {
    color: var(--text-muted);
    font-size: 12px;
    padding: var(--space-4) 0;
  }

  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    margin-bottom: 10px;
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
    margin-bottom: var(--space-24);
  }

  .meta-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-4) var(--space-16);
    font-size: 12px;
  }

  .meta-key {
    color: var(--text-muted);
    font-weight: 500;
  }

  .meta-val {
    font-weight: 600;
  }
</style>
