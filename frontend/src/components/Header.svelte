<script lang="ts">
  interface Props {
    onnewdraft: () => void;
  }

  let { onnewdraft }: Props = $props();
</script>

<header>
  <h1>🎲 Organizador Diplomacy <span id="pending-badge">⏳ Sin jugar</span></h1>
  <button
    class="btn btn-primary"
    id="btn-new-version"
    onclick={onnewdraft}
    >➕ Nueva Lista</button
  >
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
