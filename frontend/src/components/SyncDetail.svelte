<script lang="ts">
  import { fetchChain } from "../api";
  import type { SnapshotNode } from "../types";
  import PanelLayout from "./PanelLayout.svelte";

  interface Props {
    id: number;
  }

  let { id }: Props = $props();

  let info = $state<{
    from_id: number;
    to_id: number;
    created_at: string;
  } | null>(null);
  let loading = $state(true);

  async function loadSyncInfo(): Promise<void> {
    loading = true;
    try {
      const chain = await fetchChain();
      function findSync(roots: SnapshotNode[]): void {
        for (const root of roots) {
          for (const branch of root.branches ?? []) {
            if (branch.edge.type === "sync" && branch.edge.id === id) {
              info = {
                from_id: branch.edge.from_id,
                to_id: branch.edge.to_id,
                created_at: branch.edge.created_at,
              };
            }
            if (branch.output) findSync([branch.output]);
          }
        }
      }
      findSync(chain.roots ?? []);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void loadSyncInfo();
  });
</script>

{#if loading}
  <p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>
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
