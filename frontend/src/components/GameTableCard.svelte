<script lang="ts">
  import type { Snippet } from "svelte";
  import Badge from "./Badge.svelte";

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
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 11px 13px;
    margin-bottom: 10px;
  }
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .card-title {
    font-weight: 700;
    font-size: 13px;
  }
</style>
