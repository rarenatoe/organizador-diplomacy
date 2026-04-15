<script lang="ts">
  import type { Snippet } from "svelte";
  let { children }: { children: Snippet } = $props();
</script>

<div class="card-grid-item">
  {@render children()}
</div>

<style>
  .card-grid-item {
    min-width: 0;
    max-width: 100%;
    width: 100%;
  }
</style>
