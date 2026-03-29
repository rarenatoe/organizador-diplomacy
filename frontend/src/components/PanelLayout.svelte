<script lang="ts">
  import type { Snippet } from 'svelte';
  
  let { header, body, footer, scrollable = true }: {
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
    padding: 16px 18px 0;
    flex-shrink: 0;
  }

  .panel-scroll {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    padding: 16px 18px;
  }

  .panel-footer {
    flex-shrink: 0;
    padding: 16px 18px;
    border-top: 1px solid var(--border);
    background: var(--surface);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
</style>
