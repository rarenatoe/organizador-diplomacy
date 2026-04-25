import { describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen } from "@testing-library/svelte";

import SyncResolutionModal from "./SyncResolutionModal.svelte";

describe("SyncResolutionModal", () => {
  const mockPairs = [
    {
      notion_id: "notion-1",
      notion_name: "Juan Pérez",
      snapshot: "Juan Perez",
      similarity: 0.95,
      match_method: "exact",
    },
    {
      notion_id: "notion-2",
      notion_name: "María García",
      snapshot: "Maria Garcia",
      similarity: 0.85,
      match_method: "fuzzy",
    },
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
    const firstPair = mockPairs[0];
    expect(firstPair).toBeDefined();
    if (!firstPair) return;
    render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: [firstPair],
        onComplete,
        onCancel: vi.fn(),
      },
    });

    // Click merge Notion button
    const mergeBtn = screen.getByRole("button", {
      name: /Vincular & Renombrar/i,
    });
    await fireEvent.click(mergeBtn);

    expect(onComplete).toHaveBeenCalledWith([
      {
        from: "Juan Perez",
        to: "Juan Pérez",
        action: "link_rename",
        notion_id: "notion-1",
      },
    ]);
  });

  it("calls onComplete with merges when all resolved (Local name)", async () => {
    const onComplete = vi.fn();
    const firstPair = mockPairs[0];
    expect(firstPair).toBeDefined();
    if (!firstPair) return;
    render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: [firstPair],
        onComplete,
        onCancel: vi.fn(),
      },
    });

    // Click merge local button
    const mergeBtn = screen.getByRole("button", { name: /Vincular Solo/i });
    await fireEvent.click(mergeBtn);

    expect(onComplete).toHaveBeenCalledWith([
      {
        from: "Juan Perez",
        to: "Juan Pérez",
        action: "link_only",
        notion_id: "notion-1",
      },
    ]);
  });

  it("calls onComplete with empty array when all skipped", async () => {
    const onComplete = vi.fn();
    const firstPair = mockPairs[0];
    expect(firstPair).toBeDefined();
    if (!firstPair) return;
    render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: [firstPair],
        onComplete,
        onCancel: vi.fn(),
      },
    });

    // Click skip button
    const skipBtn = screen.getByRole("button", {
      name: /Añadir sin vincular/i,
    });
    await fireEvent.click(skipBtn);

    expect(onComplete).toHaveBeenCalledWith([]);
  });

  it("calls onCancel when stop button clicked", async () => {
    const onCancel = vi.fn();
    render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel,
      },
    });

    const stopBtn = screen.getByRole("button", { name: /Detener resolución/i });
    await fireEvent.click(stopBtn);

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
    const mergeBtn = screen.getByRole("button", {
      name: /Vincular & Renombrar/i,
    });
    await fireEvent.click(mergeBtn);

    // Should show second pair
    expect(container.textContent).toContain("María García");
    expect(container.textContent).toContain("Conflicto 2 de 2");
  });

  describe("Modal Snippets", () => {
    it("should render Autocorrect View when existing_local_name exists", () => {
      const autocorrectPairs = [
        {
          notion_id: "notion-1",
          notion_name: "Juan Pérez",
          snapshot: "Juan Perez",
          similarity: 0.95,
          match_method: "exact",
          existing_local_name: "Local Name", // This triggers autocorrect view
        },
      ];

      const { container } = render(SyncResolutionModal, {
        props: {
          visible: true,
          pairs: autocorrectPairs,
          onComplete: vi.fn(),
          onCancel: vi.fn(),
        },
      });

      // Should render "Usar Local Name" button for autocorrect
      expect(container.textContent).toContain("Usar Local Name");
      expect(container.querySelector(".comparison-card")).toBeTruthy();

      // Should NOT contain "Vincular & Renombrar" in autocorrect view
      expect(container.textContent).not.toContain("Vincular & Renombrar");
    });

    it("should render Standard View when existing_local_name is undefined", () => {
      const standardPairs = [
        {
          notion_id: "notion-1",
          notion_name: "Juan Pérez",
          snapshot: "Juan Perez",
          similarity: 0.95,
          match_method: "exact",
          // existing_local_name is undefined - triggers standard view
        },
      ];

      const { container } = render(SyncResolutionModal, {
        props: {
          visible: true,
          pairs: standardPairs,
          onComplete: vi.fn(),
          onCancel: vi.fn(),
        },
      });

      // Should render both "Vincular & Renombrar" and "Vincular Solo" for standard view
      expect(container.textContent).toContain("Vincular & Renombrar");
      expect(container.textContent).toContain("Vincular Solo");
      expect(container.querySelector(".comparison-card")).toBeTruthy();
    });
  });

  it("skips remaining matches for the same player if linked", async () => {
    const onComplete = vi.fn();
    const pairs = [
      {
        snapshot: "aor",
        notion_id: "notion-1",
        notion_name: "Aortheru",
        similarity: 0.9,
        match_method: "fuzzy",
      },
      {
        snapshot: "aor",
        notion_id: "notion-2",
        notion_name: "Aitor",
        similarity: 0.8,
        match_method: "fuzzy",
      },
      {
        snapshot: "bob",
        notion_id: "notion-3",
        notion_name: "Bobby",
        similarity: 0.9,
        match_method: "fuzzy",
      },
    ];

    render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs,
        onComplete,
        onCancel: vi.fn(),
      },
    });

    // 1st pair: 'aor' vs 'Aortheru'. Select Link -> This MUST skip 'aor' vs 'Aitor'
    await fireEvent.click(screen.getByText("Vincular & Renombrar"));

    // Ensure it immediately jumped to 'bob' vs 'Bobby'
    expect(screen.getAllByText("bob").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Bobby").length).toBeGreaterThan(0);

    // 2nd pair: 'bob' vs 'Bobby'. Select Link
    await fireEvent.click(screen.getByText("Vincular & Renombrar"));

    // It should complete with exactly 2 merges, successfully dropping 'Aitor'
    expect(onComplete).toHaveBeenCalledWith([
      expect.objectContaining({
        from: "aor",
        to: "Aortheru",
        action: "link_rename",
      }),
      expect.objectContaining({
        from: "bob",
        to: "Bobby",
        action: "link_rename",
      }),
    ]);
  });
});
