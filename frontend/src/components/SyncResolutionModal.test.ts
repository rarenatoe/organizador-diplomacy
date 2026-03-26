import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import SyncResolutionModal from "./SyncResolutionModal.svelte";

describe("SyncResolutionModal.svelte", () => {
  const mockPairs = [
    { notion: "Juan Pérez", snapshot: "Juan Perez", similarity: 0.95 },
    { notion: "María García", snapshot: "Maria Garcia", similarity: 0.85 },
  ];

  it("does not render when visible is false", () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: false,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    expect(container.querySelector(".resolution-overlay")).toBeNull();
  });

  it("renders when visible is true", () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    expect(container.querySelector(".resolution-overlay")).toBeTruthy();
    expect(container.querySelector(".resolution-card")).toBeTruthy();
  });

  it("shows first conflict pair", () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    expect(container.textContent).toContain("Juan Pérez");
    expect(container.textContent).toContain("Juan Perez");
  });

  it("shows conflict counter", () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    expect(container.textContent).toContain("Conflicto 1 de 2");
  });

  it("shows similarity percentage", () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    expect(container.textContent).toContain("95% similar");
  });

  it("calls onComplete with merges when all resolved (Notion name)", async () => {
    const onComplete = vi.fn();
    const firstPair = mockPairs[0]!;
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: [firstPair],
        onComplete,
        onCancel: vi.fn(),
      },
    });

    // Click merge Notion button
    const mergeBtn = container.querySelector(".resolution-btn-merge-notion");
    await fireEvent.click(mergeBtn!);

    expect(onComplete).toHaveBeenCalledWith([
      { from: "Juan Perez", to: "Juan Pérez", action: "merge_notion" },
    ]);
  });

  it("calls onComplete with merges when all resolved (Local name)", async () => {
    const onComplete = vi.fn();
    const firstPair = mockPairs[0]!;
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: [firstPair],
        onComplete,
        onCancel: vi.fn(),
      },
    });

    // Click merge local button
    const mergeBtn = container.querySelector(".resolution-btn-merge-local");
    await fireEvent.click(mergeBtn!);

    expect(onComplete).toHaveBeenCalledWith([
      { from: "Juan Perez", to: "Juan Pérez", action: "merge_local" },
    ]);
  });

  it("calls onComplete with empty array when all skipped", async () => {
    const onComplete = vi.fn();
    const firstPair = mockPairs[0]!;
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: [firstPair],
        onComplete,
        onCancel: vi.fn(),
      },
    });

    // Click skip button
    const skipBtn = container.querySelector(".resolution-btn-skip");
    await fireEvent.click(skipBtn!);

    expect(onComplete).toHaveBeenCalledWith([]);
  });

  it("calls onCancel when stop button clicked", async () => {
    const onCancel = vi.fn();
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel,
      },
    });

    const stopBtn = container.querySelector(".resolution-btn-stop");
    await fireEvent.click(stopBtn!);

    expect(onCancel).toHaveBeenCalled();
  });

  it("advances to next conflict after action", async () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    // Click merge on first pair
    const mergeBtn = container.querySelector(".resolution-btn-merge-notion");
    await fireEvent.click(mergeBtn!);

    // Should show second pair
    expect(container.textContent).toContain("María García");
    expect(container.textContent).toContain("Conflicto 2 de 2");
  });
});
