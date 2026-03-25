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
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    const onOpenGame = vi.fn();
    const onOpenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onSelect,
        onDelete,
        onOpenGame,
        onOpenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();
    expect(container.textContent).toContain("Versión #1");
  });

  it("has active class when activeNodeId matches snapshot id", () => {
    setActiveNodeId(1);
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    const onOpenGame = vi.fn();
    const onOpenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onSelect,
        onDelete,
        onOpenGame,
        onOpenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();
    expect(nodeDiv!.classList.contains("active")).toBe(true);
  });

  it("does not have active class when activeNodeId does not match", () => {
    setActiveNodeId(99);
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    const onOpenGame = vi.fn();
    const onOpenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onSelect,
        onDelete,
        onOpenGame,
        onOpenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();
    expect(nodeDiv!.classList.contains("active")).toBe(false);
  });

  it("clicking node triggers onSelect", async () => {
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    const onOpenGame = vi.fn();
    const onOpenSync = vi.fn();

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onSelect,
        onDelete,
        onOpenGame,
        onOpenSync,
      },
    });

    const nodeDiv = container.querySelector(".node-group");
    expect(nodeDiv).not.toBeNull();

    await fireEvent.click(nodeDiv!);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(1);
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
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const paginationPill = container.querySelector(".pagination-pill");
    expect(paginationPill).not.toBeNull();
    expect(container.textContent).toContain("v3 de 3");
  });

  it("does not show pagination controls for a single-version group", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const paginationPill = container.querySelector(".pagination-pill");
    expect(paginationPill).toBeNull();
  });

  it("pagination-pill is a sibling of node-group, not a child", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const nodeGroup = container.querySelector(".node-group");
    const paginationPill = container.querySelector(".pagination-pill");
    expect(nodeGroup).not.toBeNull();
    expect(paginationPill).not.toBeNull();
    // pagination-pill must NOT be a descendant of node-group
    expect(nodeGroup!.contains(paginationPill)).toBe(false);
    // both must share the same parent (.node-wrapper)
    expect(nodeGroup!.parentElement).toBe(paginationPill!.parentElement);
  });

  it("node-wrapper wraps node-group and is present in the DOM", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const nodeWrapper = container.querySelector(".node-wrapper");
    expect(nodeWrapper).not.toBeNull();
    const nodeGroup = container.querySelector(".node-group");
    expect(nodeGroup).not.toBeNull();
    expect(nodeWrapper!.contains(nodeGroup)).toBe(true);
  });

  it("shows badge-latest badge when is_latest is true", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup, // mockGroup has is_latest: true
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const badges = container.querySelector(".node-badges");
    expect(badges).not.toBeNull();
    const latestBadge = container.querySelector(".badge-latest");
    expect(latestBadge).not.toBeNull();
    expect(latestBadge!.textContent).toContain("Actual");
  });

  it("hides badge-latest badge when is_latest is false", () => {
    const groupNotLatest = {
      versions: [
        {
          snapshot: {
            type: "snapshot" as const,
            id: 99,
            created_at: "2024-06-01 09:00:00",
            source: "manual",
            player_count: 3,
            is_latest: false,
          },
          incomingEdge: null,
        },
      ],
      branches: [],
    };

    const { container } = render(SnapshotGroupNode, {
      props: {
        group: groupNotLatest,
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const latestBadge = container.querySelector(".badge-latest");
    expect(latestBadge).toBeNull();
    // node-badges container still renders (empty)
    const badges = container.querySelector(".node-badges");
    expect(badges).not.toBeNull();
  });

  it("node-badges is inside node-group", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: mockGroup,
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const nodeGroup = container.querySelector(".node-group");
    const nodeBadges = container.querySelector(".node-badges");
    expect(nodeBadges).not.toBeNull();
    expect(nodeGroup!.contains(nodeBadges)).toBe(true);
  });

  it("initialises showing the latest (last) version", () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    // Should display snapshot id 12 (the last version) by default
    expect(container.textContent).toContain("Versión #12");
    expect(container.textContent).toContain("v3 de 3");
  });

  it("navigates to previous version when prev button is clicked", async () => {
    const onSelect = vi.fn();
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onSelect,
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const prevBtn = container.querySelector(
      ".pagination-btn",
    ) as HTMLButtonElement;
    expect(prevBtn).not.toBeNull();

    await fireEvent.click(prevBtn);

    expect(container.textContent).toContain("Versión #11");
    expect(container.textContent).toContain("v2 de 3");
    expect(onSelect).toHaveBeenCalledWith(11);
  });

  it("disables prev button on first version and next button on last version", async () => {
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onSelect: vi.fn(),
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
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
    const onSelect = vi.fn();
    const { container } = render(SnapshotGroupNode, {
      props: {
        group: multiVersionGroup,
        onSelect,
        onDelete: vi.fn(),
        onOpenGame: vi.fn(),
        onOpenSync: vi.fn(),
      },
    });

    const btns =
      container.querySelectorAll<HTMLButtonElement>(".pagination-btn");
    const prevBtn = btns[0]!;
    const nextBtn = btns[1]!;

    // Go to v1
    await fireEvent.click(prevBtn);
    await fireEvent.click(prevBtn);
    onSelect.mockClear();

    // Now navigate forward
    await fireEvent.click(nextBtn);

    expect(container.textContent).toContain("Versión #11");
    expect(onSelect).toHaveBeenCalledWith(11);
  });
});
