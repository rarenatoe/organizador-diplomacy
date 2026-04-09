<script lang="ts">
  import type { ToastState } from "../../types";
  import Button from "../ui/Button.svelte";

  interface Toast {
    id: string;
    state: ToastState;
    message: string;
    dismissible: boolean;
  }

  let toasts = $state<Toast[]>([]);

  const iconMap: Record<ToastState, string> = {
    syncing: "⟳",
    success: "✅",
    error: "❌",
  };

  function showToast(options: {
    state: ToastState;
    message: string;
    dismissible?: boolean;
  }): string {
    const id = `toast-${Date.now()}`;

    // Remove any existing toast
    toasts = [];

    const toast: Toast = {
      id,
      state: options.state,
      message: options.message,
      dismissible: options.dismissible !== false,
    };

    toasts = [toast];

    // Auto-dismiss non-syncing toasts after 4 seconds
    if (options.state !== "syncing") {
      setTimeout(() => dismissToast(id), 4000);
    }

    return id;
  }

  export function showSyncingToast(): string {
    return showToast({
      state: "syncing",
      message: "Sincronizando Notion…",
      dismissible: false,
    });
  }

  export function showSuccessToast(message: string): string {
    return showToast({ state: "success", message });
  }

  export function showErrorToast(message: string): string {
    return showToast({ state: "error", message });
  }

  export function dismissToast(id: string): void {
    toasts = toasts.filter((t) => t.id !== id);
  }

  export function dismissAll(): void {
    toasts = [];
  }
</script>

<div id="toast-container">
  {#each toasts as toast (toast.id)}
    <div class="toast toast-{toast.state}">
      <span class="toast-icon">
        {#if toast.state === "syncing"}
          <span class="toast-spinner"></span>
        {:else}
          {iconMap[toast.state]}
        {/if}
      </span>
      <span class="toast-message">{toast.message}</span>
      {#if toast.dismissible}
        <Button
          variant="ghost"
          size="sm"
          iconOnly={true}
          class="toast-close"
          onclick={() => dismissToast(toast.id)}
          icon="✕"
        />
      {/if}
    </div>
  {/each}
</div>

<style>
  #toast-container {
    position: fixed;
    top: var(--space-16);
    left: 50%;
    transform: translateX(-50%);
    z-index: 200;
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
    pointer-events: none;
    align-items: center;
  }

  .toast {
    display: flex;
    align-items: center;
    gap: var(--space-8);
    padding: var(--space-16);
    border-radius: var(--space-8);
    background: var(--bg-secondary);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border-subtle);
    font-size: 13px;
    font-weight: 500;
    pointer-events: all;
    animation: toast-in 0.25s ease;
    max-width: calc(var(--space-8) * 45);
  }

  .toast-exiting {
    animation: toast-out 0.2s ease forwards;
  }

  .toast-syncing {
    border-color: var(--primary-border);
    background: var(--info-bg-subtle);
  }

  .toast-success {
    border-color: var(--success-border);
    background: var(--success-bg-subtle);
  }

  .toast-error {
    border-color: var(--danger-border);
    background: var(--danger-bg-subtle);
  }

  .toast-icon {
    font-size: 16px;
    flex-shrink: 0;
  }

  .toast-message {
    flex: 1;
    color: var(--text-primary);
  }

  .toast-close {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 14px;
    color: var(--text-muted);
    padding: var(--space-4);
    border-radius: var(--space-4);
    flex-shrink: 0;
  }

  .toast-close:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }

  .toast-spinner {
    display: inline-block;
    width: var(--space-16);
    height: var(--space-16);
    border: 2px solid var(--ring-primary);
    border-top-color: var(--primary-border);
    border-radius: 50%;
    animation: spin 0.65s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes toast-in {
    from {
      opacity: 0;
      transform: translateY(calc(-1 * var(--space-16) - var(--space-4)));
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes toast-out {
    from {
      opacity: 1;
      transform: translateY(0);
    }
    to {
      opacity: 0;
      transform: translateY(calc(-1 * var(--space-16) - var(--space-4)));
    }
  }
</style>
