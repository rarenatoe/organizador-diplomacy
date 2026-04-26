import { fireEvent, render, screen } from "@testing-library/svelte";

import SyncResolutionModal from "./SyncResolutionModal.svelte";

describe("SyncResolutionModal (Grouped 1-to-N)", () => {
  // A dataset that includes a 1-to-N conflict scenario
  const mockPairs = [
    {
      notion_id: "notion-1",
      notion_name: "Daniel Eil",
      snapshot: "Daniel",
      similarity: 0.85,
      match_method: "fuzzy",
      existing_local_name: "Daniel Eil", // Triggers Autocorrect View
    },
    {
      notion_id: "notion-2",
      notion_name: "Daniel V.",
      snapshot: "Daniel",
      similarity: 0.8,
      match_method: "fuzzy",
    },
    {
      notion_id: "notion-3",
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

  it("renders when visible is true and groups conflicts correctly", () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    expect(container.querySelector(".resolution-overlay")).toBeTruthy();
    // 3 items but grouped by 2 unique snapshots ("Daniel" and "Maria Garcia")
    expect(container.textContent).toContain("Conflicto 1 de 2");
    expect(container.textContent).toContain("Coincidencias para: Daniel");
  });

  it("shows multiple radio options for a 1-to-N conflict", () => {
    render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    const radioButtons = screen.getAllByRole("radio");
    expect(radioButtons.length).toBe(2); // Daniel Eil and Daniel V.

    expect(screen.getByText("Daniel Eil")).toBeTruthy();
    expect(screen.getByText("Daniel V.")).toBeTruthy();
  });

  it("dynamically changes action buttons based on selected radio option", async () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    // By default, the 1st radio (Daniel Eil) is selected, which has an existing_local_name
    expect(container.textContent).toContain("Usar Daniel Eil");
    expect(container.textContent).not.toContain("Vincular & Renombrar");

    // Click the 2nd radio button (Daniel V.) which does NOT have an existing_local_name
    const radioButtons = screen.getAllByRole("radio");
    if (!radioButtons[1])
      throw new Error("Expected second radio button to exist");
    await fireEvent.click(radioButtons[1]);

    // The buttons should immediately swap to the Standard View
    expect(container.textContent).not.toContain("Usar Daniel Eil");
    expect(container.textContent).toContain("Vincular & Renombrar");
    expect(container.textContent).toContain("Vincular Solo");
  });

  it("advances to the next group after making a decision", async () => {
    const { container } = render(SyncResolutionModal, {
      props: {
        visible: true,
        pairs: mockPairs,
        onComplete: vi.fn(),
        onCancel: vi.fn(),
      },
    });

    // Resolve "Daniel" by clicking "Usar Daniel Eil"
    const usarBtn = screen.getByRole("button", { name: /Usar Daniel Eil/i });
    await fireEvent.click(usarBtn);

    // It should now display the next conflict group ("Maria Garcia")
    expect(container.textContent).toContain("Conflicto 2 de 2");
    expect(container.textContent).toContain("Coincidencias para: Maria Garcia");

    // Maria Garcia only has 1 option, so there should be exactly 1 radio button
    const radioButtons = screen.getAllByRole("radio");
    expect(radioButtons.length).toBe(1);
  });

  it("calls onComplete with the correct payload mapping when finished", async () => {
    const onComplete = vi.fn();
    render(SyncResolutionModal, {
      props: { visible: true, pairs: mockPairs, onComplete, onCancel: vi.fn() },
    });

    // Group 1: Change selection to "Daniel V." and click "Vincular & Renombrar"
    const radioButtons = screen.getAllByRole("radio");
    if (!radioButtons[1])
      throw new Error("Expected second radio button to exist");
    await fireEvent.click(radioButtons[1]);
    const linkRenameBtn = screen.getByRole("button", {
      name: /Vincular & Renombrar/i,
    });
    await fireEvent.click(linkRenameBtn);

    // Group 2: Maria Garcia. Click "Añadir sin vincular" (Skip)
    const skipBtn = screen.getByRole("button", {
      name: /Añadir sin vincular/i,
    });
    await fireEvent.click(skipBtn);

    // Since we skipped Group 2, the final payload should ONLY contain Group 1's decision
    expect(onComplete).toHaveBeenCalledWith([
      {
        from: "Daniel",
        to: "Daniel V.", // Chosen Notion name
        action: "link_rename",
        notion_id: "notion-2", // The ID of the 2nd radio option
      },
    ]);
  });
});
