<script lang="ts">
  import type { ToastState } from "../types";

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
        <button
          class="toast-close"
          data-toast-id={toast.id}
          onclick={() => dismissToast(toast.id)}>✕</button
        >
      {/if}
    </div>
  {/each}
</div>

<style>
  #toast-container {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 200;
    display: flex;
    flex-direction: column;
    gap: 8px;
    pointer-events: none;
  }

  .toast {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-radius: 10px;
    background: var(--surface);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border);
    font-size: 13px;
    font-weight: 500;
    pointer-events: all;
    animation: toast-in 0.25s ease;
    max-width: 360px;
  }

  .toast-exiting {
    animation: toast-out 0.2s ease forwards;
  }

  .toast-syncing {
    border-color: var(--accent);
    background: #eff6ff;
  }

  .toast-success {
    border-color: var(--success);
    background: #f0fdf4;
  }

  .toast-error {
    border-color: var(--danger);
    background: #fef2f2;
  }

  .toast-icon {
    font-size: 16px;
    flex-shrink: 0;
  }

  .toast-message {
    flex: 1;
    color: var(--text);
  }

  .toast-close {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 14px;
    color: var(--muted);
    padding: 2px 4px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .toast-close:hover {
    color: var(--text);
    background: var(--surface2);
  }

  .toast-spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(59, 130, 246, 0.3);
    border-top-color: var(--accent);
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
      transform: translateX(20px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes toast-out {
    from {
      opacity: 1;
      transform: translateX(0);
    }
    to {
      opacity: 0;
      transform: translateX(20px);
    }
  }
</style>
