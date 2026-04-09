<script lang="ts">
  import Button from "../ui/Button.svelte";

  interface Props {
    onNewDraft: () => void;
  }

  let { onNewDraft }: Props = $props();
</script>

<header>
  <h1>🎲 Organizador Diplomacy <span id="pending-badge">⏳ Sin jugar</span></h1>
  <Button variant="primary" onclick={onNewDraft} icon="➕">Nueva Lista</Button>
</header>

<style>
  header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    padding: var(--space-16);
    gap: var(--space-8);
    box-shadow: var(--shadow-base);
    flex-shrink: 0;
    z-index: 10;
  }

  header h1 {
    font-size: 17px;
    font-weight: 700;
    flex: 1;
    display: flex;
    align-items: center;
    gap: var(--space-8);
  }

  #pending-badge {
    font-size: 11px;
    font-weight: 600;
    background: var(--warning-bg);
    color: var(--warning-text);
    border: 1px solid var(--pending-border);
    padding: var(--space-4) var(--space-8);
    border-radius: var(--space-16);
    display: none;
  }

  :global(#pending-badge.visible) {
    display: inline-block;
  }
</style>
