<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    header,
    body,
    footer,
    scrollable = true,
  }: {
    header?: Snippet;
    body: Snippet;
    footer?: Snippet;
    scrollable?: boolean;
  } = $props();
</script>

<div class="panel-layout">
  {#if header}
    <div class="panel-body-fixed">{@render header()}</div>
  {/if}

  {#if scrollable}
    <div class="panel-scroll">{@render body()}</div>
  {:else}
    {@render body()}
  {/if}

  {#if footer}
    <div class="panel-footer">{@render footer()}</div>
  {/if}
</div>

<style>
  .panel-layout {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    width: 100%;
  }

  .panel-body-fixed {
    padding: var(--space-16) var(--space-16) 0 var(--space-16);
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-24);
  }

  .panel-scroll {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    padding: var(--space-16);
    display: flex;
    flex-direction: column;
    gap: var(--space-24);
  }

  .panel-footer {
    flex-shrink: 0;
    padding: var(--space-16);
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
  }
</style>
