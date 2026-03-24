import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import SnapshotGroupNode from "./SnapshotGroupNode.svelte";
import { setActiveNodeId } from "../stores.svelte";

describe("SnapshotGroupNode", () => {
  beforeEach(() => {
    setActiveNodeId(null);
  });

  const mockGroup = {
    versions: [
      {
        snapshot: {
          type: "snapshot" as const,
          id: 1,
          created_at: "2024-01-01 10:00:00",
          source: "manual",
          player_count: 5,
          is_latest: true,
        },
        incomingEdge: null,
      },
    ],
    branches: [],
  };

  it("renders snapshot node correctly", () => {
    const onselect = vi.fn();
    const ondelete = vi.fn();
    const onopenGame = vi.fn();
    const onopenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onselect,
        ondelete,
        onopenGame,
        onopenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();
    expect(container.textContent).toContain("Versión #1");
  });

  it("has active class when activeNodeId matches snapshot id", () => {
    setActiveNodeId("snapshot-1");
    const onselect = vi.fn();
    const ondelete = vi.fn();
    const onopenGame = vi.fn();
    const onopenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onselect,
        ondelete,
        onopenGame,
        onopenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();
    expect(nodeDiv!.classList.contains("active")).toBe(true);
  });

  it("does not have active class when activeNodeId does not match", () => {
    setActiveNodeId("99");
    const onselect = vi.fn();
    const ondelete = vi.fn();
    const onopenGame = vi.fn();
    const onopenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onselect,
        ondelete,
        onopenGame,
        onopenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();
    expect(nodeDiv!.classList.contains("active")).toBe(false);
  });

  it("clicking node triggers onselect", async () => {
    const onselect = vi.fn();
    const ondelete = vi.fn();
    const onopenGame = vi.fn();
    const onopenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onselect,
        ondelete,
        onopenGame,
        onopenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();

    await fireEvent.click(nodeDiv!);

    expect(onselect).toHaveBeenCalledTimes(1);
    expect(onselect).toHaveBeenCalledWith(1);
  });

  const multiVersionGroup = {
    versions: [
      {
        snapshot: {
          type: "snapshot" as const,
          id: 10,
          created_at: "2024-01-01 10:00:00",
          source: "notion_sync",
          player_count: 5,
          is_latest: false,
        },
        incomingEdge: null,
      },
      {
        snapshot: {
          type: "snapshot" as const,
          id: 11,
          created_at: "2024-01-02 10:00:00",
          source: "organizar",
          player_count: 6,
          is_latest: false,
        },
        incomingEdge: null,
      },
      {
        snapshot: {
          type: "snapshot" as const,
          id: 12,
          created_at: "2024-01-03 10:00:00",
          source: "manual",
          player_count: 7,
          is_latest: true,
        },
        incomingEdge: null,
      },
    ],
    branches: [],
  };

  it("shows pagination controls when group has multiple versions", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onselect: vi.fn(),
        ondelete: vi.fn(),
        onopenGame: vi.fn(),
        onopenSync: vi.fn(),
      },
    });

    const paginationHeader = container.querySelector(".pagination-header");
    expect(paginationHeader).not.toBeNull();
    expect(container.textContent).toContain("v3 de 3");
  });

  it("does not show pagination controls for a single-version group", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onselect: vi.fn(),
        ondelete: vi.fn(),
        onopenGame: vi.fn(),
        onopenSync: vi.fn(),
      },
    });

    const paginationHeader = container.querySelector(".pagination-header");
    expect(paginationHeader).toBeNull();
  });

  it("initialises showing the latest (last) version", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onselect: vi.fn(),
        ondelete: vi.fn(),
        onopenGame: vi.fn(),
        onopenSync: vi.fn(),
      },
    });

    // Should display snapshot id 12 (the last version) by default
    expect(container.textContent).toContain("Versión #12");
    expect(container.textContent).toContain("v3 de 3");
  });

  it("navigates to previous version when prev button is clicked", async () => {
    const onselect = vi.fn();
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onselect,
        ondelete: vi.fn(),
        onopenGame: vi.fn(),
        onopenSync: vi.fn(),
      },
    });

    const prevBtn = container.querySelector(
      ".pagination-btn",
    ) as HTMLButtonElement;
    expect(prevBtn).not.toBeNull();

    await fireEvent.click(prevBtn);

    expect(container.textContent).toContain("Versión #11");
    expect(container.textContent).toContain("v2 de 3");
    expect(onselect).toHaveBeenCalledWith(11);
  });

  it("disables prev button on first version and next button on last version", async () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onselect: vi.fn(),
        ondelete: vi.fn(),
        onopenGame: vi.fn(),
        onopenSync: vi.fn(),
      },
    });

    const btns =
      container.querySelectorAll<HTMLButtonElement>(".pagination-btn");
    const prevBtn = btns[0]!;
    const nextBtn = btns[1]!;
    // On last version: prev enabled, next disabled
    expect(prevBtn.disabled).toBe(false);
    expect(nextBtn.disabled).toBe(true);

    // Navigate to first version
    await fireEvent.click(prevBtn);
    await fireEvent.click(prevBtn);

    // On first version: prev disabled, next enabled
    expect(prevBtn.disabled).toBe(true);
    expect(nextBtn.disabled).toBe(false);
  });

  it("navigates forward with next button", async () => {
    const onselect = vi.fn();
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onselect,
        ondelete: vi.fn(),
        onopenGame: vi.fn(),
        onopenSync: vi.fn(),
      },
    });

    const btns =
      container.querySelectorAll<HTMLButtonElement>(".pagination-btn");
    const prevBtn = btns[0]!;
    const nextBtn = btns[1]!;

    // Go to v1
    await fireEvent.click(prevBtn);
    await fireEvent.click(prevBtn);
    onselect.mockClear();

    // Now navigate forward
    await fireEvent.click(nextBtn);

    expect(container.textContent).toContain("Versión #11");
    expect(onselect).toHaveBeenCalledWith(11);
  });
});
