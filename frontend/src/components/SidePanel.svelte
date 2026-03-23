<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    title: string;
    open: boolean;
    onclose: () => void;
    children: Snippet;
  }

  let { title, open, onclose, children }: Props = $props();
</script>

<aside class="panel" class:open>
  <div class="panel-inner">
    <div class="panel-header">
      <h2 id="panel-title">{title}</h2>
      <button class="btn btn-ghost" id="btn-close-panel" onclick={onclose}
        >✕</button
      >
    </div>
    <div class="panel-body" id="panel-body">
      {@render children()}
    </div>
  </div>
</aside>

<style>
  .panel {
    width: 0;
    overflow: hidden;
    border-left: 1px solid var(--border);
    background: var(--surface);
    transition: width 0.25s ease;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  .panel.open {
    width: var(--panel-w);
  }

  .panel-inner {
    width: var(--panel-w);
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .panel-header {
    padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .panel-header h2 {
    font-size: 14px;
    font-weight: 700;
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex: 1;
    padding: 0;
  }

  :global(.panel-scroll) {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    padding: 16px 18px;
  }

  :global(.panel-body-fixed) {
    padding: 16px 18px 0;
    flex-shrink: 0;
  }

  :global(.panel-footer) {
    flex-shrink: 0;
    padding: 16px 18px;
    border-top: 1px solid var(--border);
    background: var(--surface);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
</style>
