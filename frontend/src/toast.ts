import type { ToastState, ToastOptions } from "./types";

// ── Toast container reference ────────────────────────────────────────────────

function getContainer(): HTMLElement {
  return document.getElementById("toast-container")!;
}

// ── Show a toast notification ────────────────────────────────────────────────

let activeToastId: string | null = null;

export function showToast(options: ToastOptions): string {
  const container = getContainer();
  const id = `toast-${Date.now()}`;

  // Remove any existing toast
  if (activeToastId) {
    const existing = document.getElementById(activeToastId);
    if (existing) existing.remove();
  }

  const toast = document.createElement("div");
  toast.id = id;
  toast.className = `toast toast-${options.state}`;

  const iconMap: Record<ToastState, string> = {
    syncing: "⟳",
    success: "✅",
    error: "❌",
  };

  const spinner =
    options.state === "syncing" ? '<span class="toast-spinner"></span>' : "";

  toast.innerHTML = `
    <span class="toast-icon">${spinner || iconMap[options.state]}</span>
    <span class="toast-message">${options.message}</span>
    ${options.dismissible !== false ? `<button class="toast-close" data-toast-id="${id}">✕</button>` : ""}
  `;

  container.appendChild(toast);
  activeToastId = id;

  // Auto-dismiss non-syncing toasts after 4 seconds
  if (options.state !== "syncing") {
    setTimeout(() => dismissToast(id), 4000);
  }

  return id;
}

// ── Dismiss a toast ──────────────────────────────────────────────────────────

export function dismissToast(id: string): void {
  const toast = document.getElementById(id);
  if (!toast) return;
  toast.classList.add("toast-exiting");
  setTimeout(() => {
    toast.remove();
    if (activeToastId === id) activeToastId = null;
  }, 200);
}

// ── Convenience helpers ──────────────────────────────────────────────────────

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

// ── Close button listener (delegated) ────────────────────────────────────────

document.addEventListener("click", (e: Event) => {
  const btn = (e.target as Element).closest<HTMLButtonElement>(".toast-close");
  if (!btn) return;
  const toastId = btn.dataset["toastId"];
  if (toastId) dismissToast(toastId);
});
