<script lang="ts">
  import Button from "../ui/Button.svelte";

  interface Props {
    visible: boolean;
    title: string;
    output: string;
    isError: boolean;
    loading: boolean;
    onClose: () => void;
  }

  let { visible, title, output, isError, loading, onClose }: Props = $props();
</script>

{#if visible}
  <div class="modal-overlay open">
    <div class="modal-box">
      <div class="modal-title">
        {#if loading}
          <span class="spinner"></span>
        {:else if isError}
          <span>❌</span>
        {:else}
          <span>✅</span>
        {/if}
        <span id="modal-title-text">{title}</span>
      </div>
      <div class="modal-out" class:err={isError} id="modal-out">{output}</div>
      <div class="modal-foot">
        <Button variant="secondary" onclick={onClose} disabled={loading}>
          Cerrar
        </Button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: var(--modal-backdrop);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
  }

  .modal-overlay.open {
    opacity: 1;
    pointer-events: all;
  }

  .modal-box {
    background: #1a1b2e;
    border-radius: 14px;
    padding: 22px;
    width: 560px;
    max-width: 90vw;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  }

  .modal-title {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .modal-out {
    font-family: "SF Mono", "Fira Code", Menlo, monospace;
    font-size: 12px;
    color: #a8e6cf;
    background: #0d0d1a;
    border-radius: 8px;
    padding: 12px;
    min-height: 100px;
    max-height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
  }

  .modal-out.err {
    color: #ff8a80;
  }

  .modal-foot {
    display: flex;
    justify-content: flex-end;
  }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.65s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
