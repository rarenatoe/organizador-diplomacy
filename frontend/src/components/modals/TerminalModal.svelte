<script lang="ts" module>
  // Export the union type so orchestrators can strongly-type their state
  export type TerminalState =
    | { status: "hidden" }
    | { status: "loading"; title: string }
    | { status: "success"; title: string; output: string }
    | { status: "error"; title: string; output: string };
</script>

<script lang="ts">
  import Button from "../ui/Button.svelte";

  interface Props {
    state: TerminalState;
    onClose: () => void;
  }

  let { state, onClose }: Props = $props();

  // Derived state bindings to simplify the template
  let isVisible = $derived(state.status !== "hidden");
  let isError = $derived(state.status === "error");
  let isLoading = $derived(state.status === "loading");

  // Safely narrow properties based on state types
  let title = $derived(state.status !== "hidden" ? state.title : "");
  let output = $derived("output" in state ? state.output : "");
</script>

{#if isVisible}
  <div class="modal-overlay open">
    <div class="modal-box">
      <div class="modal-title">
        {#if isLoading}
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
        <Button variant="secondary" onclick={onClose} disabled={isLoading}>
          Cerrar
        </Button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Existing styles preserved */
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
    border-radius: var(--space-16);
    padding: var(--space-24);
    width: 100%;
    max-width: calc(var(--space-8) * 70);
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
    box-shadow: var(--shadow-xl);
  }
  .modal-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-inverse);
    display: flex;
    align-items: center;
    gap: var(--space-8);
  }
  .modal-out {
    font-family: "SF Mono", "Fira Code", Menlo, monospace;
    font-size: 12px;
    color: var(--success-text);
    background: var(--gray-800);
    border-radius: var(--space-8);
    padding: var(--space-16);
    min-height: var(--space-96);
    max-height: calc(var(--space-8) * 35);
    overflow-y: auto;
    white-space: pre-wrap;
    flex-grow: 1;
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
    width: var(--space-16);
    height: var(--space-16);
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
