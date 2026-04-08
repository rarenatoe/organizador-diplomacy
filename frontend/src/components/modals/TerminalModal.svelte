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
    background: var(--bg-inverse);
    border-radius: 14px;
    padding: 22px;
    width: 560px;
    max-width: 90vw;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: var(--shadow-xl);
  }

  .modal-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-inverse);
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .modal-out {
    font-family: "SF Mono", "Fira Code", Menlo, monospace;
    font-size: 12px;
    color: var(--success-text);
    background: var(--gray-800);
    border-radius: 8px;
    padding: 12px;
    min-height: 100px;
    max-height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
  }

  .modal-out.err {
    color: var(--danger-text);
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
    border-top-color: var(--text-inverse);
    border-radius: 50%;
    animation: spin 0.65s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
