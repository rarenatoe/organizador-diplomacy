<script lang="ts">
  import type { Snippet } from "svelte";
  import { clickOutside } from "../../clickOutside";
  import Button from "../ui/Button.svelte";

  interface Props {
    title: string;
    open: boolean;
    onClose: () => void;
    children: Snippet;
  }

  let { title, open, onClose, children }: Props = $props();
</script>

<aside
  class="panel"
  class:open
  use:clickOutside={{
    ignoreSelectors: [".node", "header", ".modal-overlay", ".toast"],
    callback: () => {
      if (open) onClose();
    },
  }}
>
  <div class="panel-inner">
    <div class="panel-header">
      <h2 id="panel-title">{title}</h2>
      <Button
        variant="ghost"
        size="sm"
        iconOnly={true}
        onclick={onClose}
        icon="✕"
        title="Cerrar"
      />
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
    position: relative;
    z-index: 50;
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
</style>
