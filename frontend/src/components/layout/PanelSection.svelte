<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children: Snippet;
    class?: string;
  }

  let { children, class: className = "" }: Props = $props();
</script>

<div class="panel-section {className}">
  {@render children()}
</div>

<style>
  .panel-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
  }
</style>
