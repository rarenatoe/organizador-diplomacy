<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children: Snippet;
    class?: string;
  }

  let { children, class: className = "" }: Props = $props();
</script>

<div class="meta-grid {className}">
  {@render children()}
</div>

<style>
  .meta-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-4) var(--space-16);
    font-size: 12px;
  }
</style>
