<script lang="ts">
  import type { Snippet } from "svelte";
  let { children }: { children: Snippet } = $props();
</script>

<div class="card-grid-container">
  {@render children()}
</div>

<style>
  .card-grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
    gap: var(--space-16);
    align-items: start;
    width: 100%;
  }
</style>
