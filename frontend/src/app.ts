import type { RunResult, SyncDetectResult, MergePair } from "./types";
import { loadChain } from "./chain";
import {
  getSelectedSnapshot,
  setSelectedSnapshot,
  deselectSnapshot,
} from "./selection";
import {
  closePanel,
  openSnapshot,
  openSyncPanel,
  openGame,
  deleteSnapshot,
} from "./panels";
import {
  showSyncingToast,
  showSuccessToast,
  showErrorToast,
  dismissToast,
} from "./toast";
import { startResolution } from "./resolution";

// ── Node click ────────────────────────────────────────────────────────────────

document.getElementById("chain")!.addEventListener("click", (e: MouseEvent) => {
  const delBtn = (e.target as Element).closest<HTMLElement>(".node-delete-btn");
  if (delBtn) {
    const id = parseInt(delBtn.dataset["snapshotId"] ?? "", 10);
    void deleteSnapshot(id);
    return;
  }
  const node = (e.target as Element).closest<HTMLElement>(".node");
  if (!node) return;
  const idStr = node.dataset["id"] ?? "";
  const id = parseInt(idStr, 10);
  const type = node.dataset["type"];
  setActive(idStr);
  if (type === "snapshot") {
    setSelectedSnapshot(id);
    void openSnapshot(id);
  } else if (type === "sync") {
    void openSyncPanel(id);
  } else if (type === "game") {
    void openGame(id);
  }
});

function setActive(idStr: string): void {
  document.querySelectorAll<HTMLElement>(".node").forEach((n) => {
    n.classList.remove("active");
  });
  const el = document.querySelector<HTMLElement>(
    `[data-id="${CSS.escape(idStr)}"]`,
  );
  if (el) el.classList.add("active");
}

// ── Run scripts ───────────────────────────────────────────────────────────────

const SCRIPT_LABELS: Record<string, string> = {
  notion_sync: "↻ Sync Notion",
  organizar: "▶ Organizar",
};

async function runScript(
  script: string,
  snapshotId: number | null = null,
): Promise<void> {
  const modal = document.getElementById("modal")!;
  const out = document.getElementById("modal-out")!;
  const titleEl = document.getElementById("modal-title-text")!;
  const iconEl = document.getElementById("modal-icon")!;
  const closeBtn = document.getElementById(
    "btn-modal-close",
  ) as HTMLButtonElement;
  const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
  const btnOrganizar = document.getElementById(
    "btn-organizar",
  ) as HTMLButtonElement;
  out.textContent = "";
  out.className = "modal-out";
  titleEl.textContent = `Ejecutando ${SCRIPT_LABELS[script] ?? script}…`;
  iconEl.innerHTML = '<span class="spinner"></span>';
  closeBtn.disabled = true;
  modal.classList.add("open");
  btnSync.disabled = true;
  btnOrganizar.disabled = true;
  const fetchInit: RequestInit = { method: "POST" };
  if (snapshotId !== null) {
    fetchInit.headers = { "Content-Type": "application/json" };
    fetchInit.body = JSON.stringify({ snapshot: snapshotId });
  }
  try {
    const res = await fetch(`/api/run/${script}`, fetchInit);
    const data = (await res.json()) as RunResult;
    const ok = data.returncode === 0;
    iconEl.textContent = ok ? "✅" : "❌";
    titleEl.textContent = ok
      ? `${SCRIPT_LABELS[script] ?? script} completado`
      : `Error en ${SCRIPT_LABELS[script] ?? script}`;
    out.textContent =
      (data.stdout ?? "") + (data.stderr ? "\n[stderr]\n" + data.stderr : "");
    if (!ok) out.classList.add("err");
    if (ok) await loadChain();
  } catch (e) {
    iconEl.textContent = "❌";
    titleEl.textContent = "Error de conexión";
    out.textContent = String(e);
    out.classList.add("err");
  } finally {
    closeBtn.disabled = false;
    btnSync.disabled = false;
    btnOrganizar.disabled = false;
  }
}

function closeModal(): void {
  document.getElementById("modal")!.classList.remove("open");
}

// ── Two-phase sync with toast + sequential resolution ─────────────────────────

async function detectAndSync(): Promise<void> {
  const snapshotId = getSelectedSnapshot();
  const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
  const btnOrganizar = document.getElementById(
    "btn-organizar",
  ) as HTMLButtonElement;

  btnSync.disabled = true;
  btnOrganizar.disabled = true;
  const toastId = showSyncingToast();

  try {
    const detectInit: RequestInit = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot: snapshotId }),
    };
    const detectRes = await fetch("/api/sync/detect", detectInit);
    const detectData = (await detectRes.json()) as SyncDetectResult;

    if (detectData.similar_names.length === 0) {
      // No conflicts — proceed with sync directly
      await runSyncConfirm(snapshotId, [], toastId);
    } else {
      // Conflicts found — hide syncing toast, open resolution card
      dismissToast(toastId);
      startResolution(
        detectData.similar_names,
        snapshotId,
        (merges: MergePair[]) => {
          // On resolution complete: show new syncing toast and confirm
          const newToastId = showSyncingToast();
          void runSyncConfirm(snapshotId, merges, newToastId);
        },
        () => {
          // On cancel: re-enable buttons
          btnSync.disabled = false;
          btnOrganizar.disabled = false;
        },
      );
    }
  } catch (e) {
    dismissToast(toastId);
    showErrorToast(`Error de conexión: ${String(e)}`);
    btnSync.disabled = false;
    btnOrganizar.disabled = false;
  }
}

async function runSyncConfirm(
  snapshotId: number | null,
  merges: MergePair[],
  toastId: string,
): Promise<void> {
  const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
  const btnOrganizar = document.getElementById(
    "btn-organizar",
  ) as HTMLButtonElement;

  try {
    const confirmInit: RequestInit = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot: snapshotId, merges }),
    };
    const res = await fetch("/api/sync/confirm", confirmInit);
    const data = (await res.json()) as RunResult;
    const ok = data.returncode === 0;
    dismissToast(toastId);
    if (ok) {
      showSuccessToast("Sync Notion completado");
      await loadChain();
    } else {
      showErrorToast(
        `Error en Sync Notion: ${data.stderr ?? "desconocido"}`,
      );
    }
  } catch (e) {
    dismissToast(toastId);
    showErrorToast(`Error de conexión: ${String(e)}`);
  } finally {
    btnSync.disabled = false;
    btnOrganizar.disabled = false;
  }
}

// ── Button event listeners (no onclick in HTML) ───────────────────────────────

document.getElementById("btn-refresh")!.addEventListener("click", () => {
  void loadChain();
});
document.getElementById("btn-sync")!.addEventListener("click", () => {
  void detectAndSync();
});
document.getElementById("btn-organizar")!.addEventListener("click", () => {
  void runScript("organizar", getSelectedSnapshot());
});
document
  .getElementById("btn-deselect")!
  .addEventListener("click", deselectSnapshot);
document
  .getElementById("btn-close-panel")!
  .addEventListener("click", closePanel);
document
  .getElementById("btn-modal-close")!
  .addEventListener("click", closeModal);

void loadChain();
