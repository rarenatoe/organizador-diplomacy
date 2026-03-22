import type {
  SimilarName,
  ResolutionDecision,
  ResolutionAction,
  MergePair,
} from "./types";

// ── State ────────────────────────────────────────────────────────────────────

let state: {
  pairs: SimilarName[];
  currentIndex: number;
  decisions: ResolutionDecision[];
  snapshotId: number | null;
  onComplete: (merges: MergePair[]) => void;
  onCancel: () => void;
} | null = null;

// ── DOM references ───────────────────────────────────────────────────────────

function getOverlay(): HTMLElement {
  return document.getElementById("resolution-overlay")!;
}

function getCard(): HTMLElement {
  return document.getElementById("resolution-card")!;
}

// ── Start resolution flow ────────────────────────────────────────────────────

export function startResolution(
  pairs: SimilarName[],
  snapshotId: number | null,
  onComplete: (merges: MergePair[]) => void,
  onCancel: () => void,
): void {
  state = {
    pairs,
    currentIndex: 0,
    decisions: [],
    snapshotId,
    onComplete,
    onCancel,
  };
  renderCard();
  getOverlay().classList.add("visible");
}

// ── Close resolution ─────────────────────────────────────────────────────────

export function closeResolution(): void {
  getOverlay().classList.remove("visible");
  state = null;
}

// ── Render current card ──────────────────────────────────────────────────────

function renderCard(): void {
  if (!state) return;
  const { pairs, currentIndex } = state;
  const total = pairs.length;
  const pair = pairs[currentIndex];
  if (!pair) return;
  const similarity = Math.round(pair.similarity * 100);

  const card = getCard();
  card.innerHTML = `
    <div class="resolution-header">
      <span class="resolution-icon">🔍</span>
      <span class="resolution-title">Nombres similares</span>
    </div>
    <div class="resolution-counter">Conflicto ${currentIndex + 1} de ${total}</div>
    <div class="resolution-pair">
      <div class="resolution-side">
        <span class="resolution-label">Notion</span>
        <span class="resolution-name resolution-name-notion">${esc(pair.notion)}</span>
      </div>
      <div class="resolution-vs">vs</div>
      <div class="resolution-side">
        <span class="resolution-label">Snapshot</span>
        <span class="resolution-name resolution-name-snapshot">${esc(pair.snapshot)}</span>
      </div>
    </div>
    <div class="resolution-similarity">${similarity}% similar</div>
    <div class="resolution-actions">
      <button class="btn btn-primary resolution-btn-merge" data-action="merge">
        🔀 Fusionar
      </button>
      <button class="btn btn-secondary resolution-btn-skip" data-action="skip">
        ⏭ Omitir
      </button>
    </div>
    <div class="resolution-footer">
      <button class="btn btn-ghost resolution-btn-stop">Detener resolución</button>
    </div>
  `;
}

// ── Handle action (merge/skip) ───────────────────────────────────────────────

function handleAction(action: ResolutionAction): void {
  if (!state) return;
  const pair = state.pairs[state.currentIndex];
  if (!pair) return;
  state.decisions.push({ pair, action });

  if (state.currentIndex < state.pairs.length - 1) {
    state.currentIndex++;
    renderCard();
  } else {
    // All pairs resolved — build merges and call onComplete
    const merges: MergePair[] = state.decisions
      .filter((d) => d.action === "merge")
      .map((d) => ({ from: d.pair.snapshot, to: d.pair.notion }));
    const onComplete = state.onComplete;
    closeResolution();
    onComplete(merges);
  }
}

// ── Event listeners (delegated) ──────────────────────────────────────────────

document.addEventListener("click", (e: Event) => {
  const target = e.target as Element;

  // Merge button
  if (target.closest(".resolution-btn-merge")) {
    handleAction("merge");
    return;
  }

  // Skip button
  if (target.closest(".resolution-btn-skip")) {
    handleAction("skip");
    return;
  }

  // Stop resolution
  if (target.closest(".resolution-btn-stop")) {
    if (state) {
      const onCancel = state.onCancel;
      closeResolution();
      onCancel();
    }
    return;
  }
});

// ── Escape helper ────────────────────────────────────────────────────────────

function esc(s: string): string {
  const el = document.createElement("span");
  el.textContent = s;
  return el.innerHTML;
}
