<script lang="ts">
  import type { Snippet } from "svelte";
  import Badge from "../ui/Badge.svelte";

  interface Props {
    tableNumber: number | string;
    gmName: string | null;
    children?: Snippet;
  }

  let { tableNumber, gmName, children }: Props = $props();
</script>

<div class="card">
  <div class="card-header">
    <span class="card-title">Partida {tableNumber}</span>
    {#if gmName}
      <Badge variant="info" text={`GM: ${gmName}`} pill={true} />
    {:else}
      <Badge variant="error" text="⚠️ Sin GM" pill={true} />
    {/if}
  </div>
  {#if children}
    {@render children()}
  {/if}
</div>

<style>
  .card {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-default);
    border-radius: var(--space-8);
    padding: var(--space-8) var(--space-16);
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
  }
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-8);
  }
  .card-title {
    font-weight: 700;
    font-size: 13px;
  }
</style>
