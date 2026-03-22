import { describe, it, expect, beforeEach, vi } from "vitest";
import type { SimilarName, MergePair } from "./types";

function setupDOM(): void {
  document.body.innerHTML = `
    <div class="resolution-overlay" id="resolution-overlay">
      <div class="resolution-card" id="resolution-card"></div>
    </div>
  `;
}

const mockPairs: SimilarName[] = [
  { notion: "Kurt", snapshot: "Kur", similarity: 1.0 },
  { notion: "Renato Alegre", snapshot: "Ren Alegre", similarity: 1.0 },
  { notion: "Paul Knight", snapshot: "P. Knight", similarity: 1.0 },
];

describe("resolution module", () => {
  beforeEach(() => {
    setupDOM();
  });

  it("startResolution shows overlay and renders first card", async () => {
    const { startResolution } = await import("./resolution");
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(mockPairs, null, onComplete, onCancel);

    const overlay = document.getElementById("resolution-overlay")!;
    expect(overlay.classList.contains("visible")).toBe(true);

    const card = document.getElementById("resolution-card")!;
    expect(card.textContent).toContain("Kurt");
    expect(card.textContent).toContain("Kur");
    expect(card.textContent).toContain("Conflicto 1 de 3");
  });

  it("merge button advances to next pair", async () => {
    const { startResolution } = await import("./resolution");
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(mockPairs, null, onComplete, onCancel);

    // Click merge
    const mergeBtn = document.querySelector(".resolution-btn-merge")!;
    mergeBtn.dispatchEvent(new Event("click", { bubbles: true }));

    // Should show second pair
    const card = document.getElementById("resolution-card")!;
    expect(card.textContent).toContain("Renato Alegre");
    expect(card.textContent).toContain("Ren Alegre");
    expect(card.textContent).toContain("Conflicto 2 de 3");
  });

  it("skip button advances to next pair without merging", async () => {
    const { startResolution } = await import("./resolution");
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(mockPairs, null, onComplete, onCancel);

    // Click skip
    const skipBtn = document.querySelector(".resolution-btn-skip")!;
    skipBtn.dispatchEvent(new Event("click", { bubbles: true }));

    // Should show second pair
    const card = document.getElementById("resolution-card")!;
    expect(card.textContent).toContain("Conflicto 2 de 3");
  });

  it("completing all pairs calls onComplete with merges", async () => {
    const { startResolution } = await import("./resolution");
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(mockPairs, null, onComplete, onCancel);

    // Merge first, skip second, merge third
    const mergeBtn = document.querySelector(".resolution-btn-merge")!;
    mergeBtn.dispatchEvent(new Event("click", { bubbles: true }));

    const skipBtn = document.querySelector(".resolution-btn-skip")!;
    skipBtn.dispatchEvent(new Event("click", { bubbles: true }));

    const mergeBtn2 = document.querySelector(".resolution-btn-merge")!;
    mergeBtn2.dispatchEvent(new Event("click", { bubbles: true }));

    // onComplete should be called with 2 merges (1st and 3rd)
    expect(onComplete).toHaveBeenCalledTimes(1);
    const merges = onComplete.mock.calls[0]![0] as MergePair[];
    expect(merges).toHaveLength(2);
    expect(merges[0]!).toEqual({ from: "Kur", to: "Kurt" });
    expect(merges[1]!).toEqual({ from: "P. Knight", to: "Paul Knight" });
  });

  it("stop button calls onCancel and closes overlay", async () => {
    const { startResolution } = await import("./resolution");
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(mockPairs, null, onComplete, onCancel);

    const stopBtn = document.querySelector(".resolution-btn-stop")!;
    stopBtn.dispatchEvent(new Event("click", { bubbles: true }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();

    const overlay = document.getElementById("resolution-overlay")!;
    expect(overlay.classList.contains("visible")).toBe(false);
  });

  it("closeResolution hides overlay and clears state", async () => {
    const { startResolution, closeResolution } = await import("./resolution");
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(mockPairs, null, onComplete, onCancel);
    const overlay = document.getElementById("resolution-overlay")!;
    expect(overlay.classList.contains("visible")).toBe(true);

    closeResolution();
    expect(overlay.classList.contains("visible")).toBe(false);
  });

  it("single pair resolution completes immediately on merge", async () => {
    const { startResolution } = await import("./resolution");
    const singlePair: SimilarName[] = [
      { notion: "Kurt", snapshot: "Kur", similarity: 1.0 },
    ];
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(singlePair, null, onComplete, onCancel);

    const mergeBtn = document.querySelector(".resolution-btn-merge")!;
    mergeBtn.dispatchEvent(new Event("click", { bubbles: true }));

    expect(onComplete).toHaveBeenCalledTimes(1);
    const merges = onComplete.mock.calls[0]![0] as MergePair[];
    expect(merges).toHaveLength(1);
    expect(merges[0]!).toEqual({ from: "Kur", to: "Kurt" });
  });

  it("single pair resolution completes immediately on skip", async () => {
    const { startResolution } = await import("./resolution");
    const singlePair: SimilarName[] = [
      { notion: "Kurt", snapshot: "Kur", similarity: 1.0 },
    ];
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(singlePair, null, onComplete, onCancel);

    const skipBtn = document.querySelector(".resolution-btn-skip")!;
    skipBtn.dispatchEvent(new Event("click", { bubbles: true }));

    expect(onComplete).toHaveBeenCalledTimes(1);
    const merges = onComplete.mock.calls[0]![0] as MergePair[];
    expect(merges).toHaveLength(0); // Skipped, no merges
  });

  it("similarity percentage is displayed correctly", async () => {
    const { startResolution } = await import("./resolution");
    const pairs: SimilarName[] = [
      { notion: "John Doe", snapshot: "John D.", similarity: 0.85 },
    ];
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    startResolution(pairs, null, onComplete, onCancel);

    const card = document.getElementById("resolution-card")!;
    expect(card.textContent).toContain("85% similar");
  });
});
