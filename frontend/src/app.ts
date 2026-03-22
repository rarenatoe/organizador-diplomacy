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

// ── Two-phase sync with merge detection ───────────────────────────────────────

async function detectAndSync(): Promise<void> {
  const snapshotId = getSelectedSnapshot();
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

  // Phase 1: Detect similar names
  out.textContent = "";
  out.className = "modal-out";
  titleEl.textContent = "Detectando nombres similares…";
  iconEl.innerHTML = '<span class="spinner"></span>';
  closeBtn.disabled = true;
  modal.classList.add("open");
  btnSync.disabled = true;
  btnOrganizar.disabled = true;

  try {
    const detectInit: RequestInit = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot: snapshotId }),
    };
    const detectRes = await fetch("/api/sync/detect", detectInit);
    const detectData = (await detectRes.json()) as SyncDetectResult;

    if (detectData.similar_names.length === 0) {
      // No similar names found, proceed with normal sync
      out.textContent = `No se encontraron nombres similares.\nJugadores en Notion: ${detectData.notion_count}\nJugadores en snapshot: ${detectData.snapshot_count}`;
      await runSyncConfirm(snapshotId, []);
    } else {
      // Show merge confirmation UI
      showMergeDialog(detectData, snapshotId);
    }
  } catch (e) {
    iconEl.textContent = "❌";
    titleEl.textContent = "Error de conexión";
    out.textContent = String(e);
    out.classList.add("err");
    closeBtn.disabled = false;
    btnSync.disabled = false;
    btnOrganizar.disabled = false;
  }
}

function showMergeDialog(
  detectData: SyncDetectResult,
  snapshotId: number | null,
): void {
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

  titleEl.textContent = "Fusionar nombres similares";
  iconEl.textContent = "🔍";

  const selectedMerges: MergePair[] = [];

  let html = `<p>Se encontraron ${detectData.similar_names.length} par(es) de nombres similares.</p>`;
  html += "<p>Selecciona los pares que deseas fusionar:</p>";
  html += '<div class="merge-list">';

  for (const pair of detectData.similar_names) {
    const similarity = Math.round(pair.similarity * 100);
    html += `
      <label class="merge-item">
        <input type="checkbox" class="merge-checkbox" data-notion="${pair.notion}" data-snapshot="${pair.snapshot}">
        <span class="merge-names">
          <strong>${pair.notion}</strong> (Notion) ↔ <strong>${pair.snapshot}</strong> (Snapshot)
        </span>
        <span class="merge-similarity">${similarity}% similar</span>
      </label>
    `;
  }

  html += "</div>";
  html += `
    <div class="merge-actions">
      <button id="btn-merge-confirm" class="btn btn-primary">Confirmar y sincronizar</button>
      <button id="btn-merge-skip" class="btn btn-secondary">Sincronizar sin fusionar</button>
      <button id="btn-merge-cancel" class="btn btn-secondary">Cancelar</button>
    </div>
  `;

  out.innerHTML = html;
  closeBtn.disabled = false;

  // Event listeners for merge dialog
  document
    .getElementById("btn-merge-confirm")!
    .addEventListener("click", () => {
      const checkboxes = document.querySelectorAll<HTMLInputElement>(
        ".merge-checkbox:checked",
      );
      checkboxes.forEach((cb) => {
        selectedMerges.push({
          from: cb.dataset["snapshot"]!,
          to: cb.dataset["notion"]!,
        });
      });
      void runSyncConfirm(snapshotId, selectedMerges);
    });

  document.getElementById("btn-merge-skip")!.addEventListener("click", () => {
    void runSyncConfirm(snapshotId, []);
  });

  document.getElementById("btn-merge-cancel")!.addEventListener("click", () => {
    closeModal();
    btnSync.disabled = false;
    btnOrganizar.disabled = false;
  });
}

async function runSyncConfirm(
  snapshotId: number | null,
  merges: MergePair[],
): Promise<void> {
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
  titleEl.textContent = "Ejecutando Sync Notion…";
  iconEl.innerHTML = '<span class="spinner"></span>';
  closeBtn.disabled = true;

  try {
    const confirmInit: RequestInit = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot: snapshotId, merges }),
    };
    const res = await fetch("/api/sync/confirm", confirmInit);
    const data = (await res.json()) as RunResult;
    const ok = data.returncode === 0;
    iconEl.textContent = ok ? "✅" : "❌";
    titleEl.textContent = ok
      ? "Sync Notion completado"
      : "Error en Sync Notion";
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
