<script lang="ts">
  import { apiChain, type SnapshotNode } from "../../generated-api";
  import PanelLayout from "../layout/PanelLayout.svelte";
  import PanelSection from "../layout/PanelSection.svelte";
  import MetaGrid from "../ui/MetaGrid.svelte";
  import MetaItem from "../ui/MetaItem.svelte";

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
      <PanelSection>
        <div class="section-title">Detalles del Sync</div>
        <MetaGrid>
          <MetaItem label="Generado" value={info?.created_at} />
          <MetaItem label="De snapshot" value={`#${info?.from_id}`} />
          <MetaItem
            label="A snapshot"
            value={info?.to_id ? `#${info?.to_id}` : "Ninguno"}
          />
        </MetaGrid>
      </PanelSection>
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
</style>
