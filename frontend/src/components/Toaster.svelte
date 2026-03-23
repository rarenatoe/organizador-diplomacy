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