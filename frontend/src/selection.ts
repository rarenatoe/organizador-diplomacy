// ── Snapshot selection ────────────────────────────────────────────────────────
// _selectedSnapshot is null → server uses the latest snapshot.
// Clicking a snapshot node selects it; ✕ button deselects.
// The selected snapshot is used as the base for both Organizar and Sync Notion.

let _selectedSnapshot: number | null = null;
let _snapshotCount: number = 0;

export function getSelectedSnapshot(): number | null {
  return _selectedSnapshot;
}

export function setSelectedSnapshot(id: number): void {
  _selectedSnapshot = id;
  updateSelectionUI();
}

export function deselectSnapshot(): void {
  _selectedSnapshot = null;
  updateSelectionUI();
}

export function setSnapshotCount(count: number): void {
  _snapshotCount = count;
  updateSyncButtonState();
}

function updateSyncButtonState(): void {
  const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
  // Enabled if: no snapshots exist (initial sync) OR a snapshot is selected
  // Disabled if: at least one snapshot exists but none are selected
  const shouldEnable = _snapshotCount === 0 || _selectedSnapshot !== null;
  btnSync.disabled = !shouldEnable;
}

export function updateSelectionUI(): void {
  document.querySelectorAll<HTMLElement>(".node-csv").forEach((n) => {
    const nodeId = parseInt(n.dataset["id"] ?? "", 10);
    n.classList.toggle("csv-selected", nodeId === _selectedSnapshot);
  });
  const label = document.getElementById("organizar-label")!;
  const deselBtn = document.getElementById("btn-deselect") as HTMLElement;
  if (_selectedSnapshot !== null) {
    label.textContent = `Organizar · #${_selectedSnapshot}`;
    deselBtn.style.display = "";
  } else {
    label.textContent = "Organizar";
    deselBtn.style.display = "none";
  }
  updateSyncButtonState();
}
