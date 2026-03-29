<script lang="ts">
  import Button from "./Button.svelte";

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
    height: var(--hdr);
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 10px;
    box-shadow: var(--shadow);
    flex-shrink: 0;
    z-index: 10;
  }

  header h1 {
    font-size: 17px;
    font-weight: 700;
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  #pending-badge {
    font-size: 11px;
    font-weight: 600;
    background: #fef3c7;
    color: #92400e;
    border: 1px solid var(--pending-border);
    padding: 2px 8px;
    border-radius: 99px;
    display: none;
  }

  :global(#pending-badge.visible) {
    display: inline-block;
  }
</style>
