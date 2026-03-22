import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock DOM elements before importing the module
function setupDOM(): void {
  document.body.innerHTML = '<div id="toast-container"></div>';
}

describe("toast module", () => {
  beforeEach(() => {
    setupDOM();
    vi.useFakeTimers();
  });

  it("showSyncingToast creates a syncing toast", async () => {
    const { showSyncingToast } = await import("./toast");
    const id = showSyncingToast();
    const toast = document.getElementById(id);
    expect(toast).not.toBeNull();
    expect(toast!.classList.contains("toast-syncing")).toBe(true);
    expect(toast!.textContent).toContain("Sincronizando Notion");
  });

  it("showSuccessToast creates a success toast", async () => {
    const { showSuccessToast } = await import("./toast");
    const id = showSuccessToast("Done!");
    const toast = document.getElementById(id);
    expect(toast).not.toBeNull();
    expect(toast!.classList.contains("toast-success")).toBe(true);
    expect(toast!.textContent).toContain("Done!");
  });

  it("showErrorToast creates an error toast", async () => {
    const { showErrorToast } = await import("./toast");
    const id = showErrorToast("Failed!");
    const toast = document.getElementById(id);
    expect(toast).not.toBeNull();
    expect(toast!.classList.contains("toast-error")).toBe(true);
    expect(toast!.textContent).toContain("Failed!");
  });

  it("dismissToast removes toast after animation", async () => {
    const { showSuccessToast, dismissToast } = await import("./toast");
    const id = showSuccessToast("Test");
    const toast = document.getElementById(id);
    expect(toast).not.toBeNull();
    dismissToast(id);
    expect(toast!.classList.contains("toast-exiting")).toBe(true);
    vi.advanceTimersByTime(250);
    expect(document.getElementById(id)).toBeNull();
  });

  it("new toast replaces previous toast", async () => {
    vi.useRealTimers(); // Use real timers for Date.now() uniqueness
    const { showSyncingToast, showSuccessToast } = await import("./toast");
    const id1 = showSyncingToast();
    expect(document.getElementById(id1)).not.toBeNull();
    const id2 = showSuccessToast("Done");
    // Old toast should be removed
    expect(document.getElementById(id1)).toBeNull();
    expect(document.getElementById(id2)).not.toBeNull();
  });

  it("syncing toast has no close button (not dismissible)", async () => {
    const { showSyncingToast } = await import("./toast");
    const id = showSyncingToast();
    const toast = document.getElementById(id);
    const closeBtn = toast!.querySelector(".toast-close");
    expect(closeBtn).toBeNull();
  });

  it("success toast has close button (dismissible)", async () => {
    const { showSuccessToast } = await import("./toast");
    const id = showSuccessToast("Done");
    const toast = document.getElementById(id);
    const closeBtn = toast!.querySelector(".toast-close");
    expect(closeBtn).not.toBeNull();
  });

  it("success toast auto-dismisses after 4 seconds", async () => {
    const { showSuccessToast } = await import("./toast");
    const id = showSuccessToast("Done");
    expect(document.getElementById(id)).not.toBeNull();
    vi.advanceTimersByTime(4000);
    // After 4s, dismissToast is called, which adds exiting class
    const toast = document.getElementById(id);
    expect(toast!.classList.contains("toast-exiting")).toBe(true);
    vi.advanceTimersByTime(250);
    expect(document.getElementById(id)).toBeNull();
  });
});
