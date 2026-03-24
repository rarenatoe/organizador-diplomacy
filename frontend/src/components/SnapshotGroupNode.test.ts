import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import SnapshotGroupNode from "./SnapshotGroupNode.svelte";
import {
  setSelectedSnapshot,
  deselectSnapshot,
  setActiveNodeId,
  getSelectedSnapshot,
} from "../stores.svelte";

describe("SnapshotGroupNode", () => {
  beforeEach(() => {
    deselectSnapshot();
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
    setActiveNodeId("1");
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

  it("has csv-selected class when snapshot is selected", () => {
    setSelectedSnapshot(1);
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
    expect(nodeDiv!.classList.contains("csv-selected")).toBe(true);
  });

  it("does not have csv-selected class when snapshot is not selected", () => {
    deselectSnapshot();
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
    expect(nodeDiv!.classList.contains("csv-selected")).toBe(false);
  });

  it("shows pin badge when snapshot is selected", () => {
    setSelectedSnapshot(1);
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

    const pinButton = container.querySelector(".badge-selected");
    expect(pinButton).not.toBeNull();
    expect(pinButton!.textContent).toContain("📌");
  });

  it("does not show pin badge when snapshot is not selected", () => {
    deselectSnapshot();
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

    const pinButton = container.querySelector(".badge-selected");
    expect(pinButton).toBeNull();
  });

  it("clicking pin badge deselects snapshot", async () => {
    setSelectedSnapshot(1);
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

    const pinButton = container.querySelector(".badge-selected");
    expect(pinButton).not.toBeNull();

    await fireEvent.click(pinButton!);

    expect(getSelectedSnapshot()).toBeNull();
  });

  it("clicking pin badge does not trigger node selection", async () => {
    setSelectedSnapshot(1);
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

    const pinButton = container.querySelector(".badge-selected");
    expect(pinButton).not.toBeNull();

    await fireEvent.click(pinButton!);

    // onselect should not be called because of e.stopPropagation()
    expect(onselect).not.toHaveBeenCalled();
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

  it("both active and csv-selected classes can coexist", () => {
    setSelectedSnapshot(1);
    setActiveNodeId("1");
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
    expect(nodeDiv!.classList.contains("csv-selected")).toBe(true);
  });
});
