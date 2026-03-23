import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import GameNode from "./GameNode.svelte";
import SyncNode from "./SyncNode.svelte";
import SnapshotNode from "./SnapshotNode.svelte";

describe("Node Interaction Seatbelts", () => {
  it("GameNode triggers onopen with correct ID when clicked", async () => {
    const onopen = vi.fn();
    const { container } = render(GameNode, {
      props: {
        node: {
          type: "game",
          id: 42,
          created_at: "2024-01-01",
          from_id: 1,
          to_id: 2,
          intentos: 1,
          mesa_count: 1,
          espera_count: 0,
        },
        onopen,
      },
    });

    const nodeDiv = container.querySelector(".node-report");
    expect(nodeDiv).not.toBeNull();
    await fireEvent.click(nodeDiv!);

    expect(onopen).toHaveBeenCalledTimes(1);
    expect(onopen).toHaveBeenCalledWith(42);
  });

  it("SyncNode triggers onopen with correct ID when clicked", async () => {
    const onopen = vi.fn();
    const { container } = render(SyncNode, {
      props: {
        node: {
          type: "sync",
          id: 99,
          created_at: "2024-01-01",
          from_id: 1,
          to_id: 2,
        },
        onopen,
      },
    });

    const nodeDiv = container.querySelector(".node-sync");
    expect(nodeDiv).not.toBeNull();
    await fireEvent.click(nodeDiv!);

    expect(onopen).toHaveBeenCalledTimes(1);
    expect(onopen).toHaveBeenCalledWith(99);
  });

  it("SnapshotNode propagates click handlers to children", async () => {
    const onopenGame = vi.fn();
    const onopenSync = vi.fn();
    const { container } = render(SnapshotNode, {
      props: {
        node: {
          type: "snapshot",
          id: 1,
          created_at: "2024-01-01",
          source: "notion_sync",
          player_count: 5,
          is_latest: false,
          branches: [
            {
              edge: {
                type: "game",
                id: 10,
                created_at: "2024-01-01",
                from_id: 1,
                to_id: 2,
                intentos: 1,
                mesa_count: 1,
                espera_count: 0,
              },
              output: null,
            },
            {
              edge: {
                type: "sync",
                id: 11,
                created_at: "2024-01-01",
                from_id: 1,
                to_id: 3,
              },
              output: null,
            },
          ],
        },
        onselect: vi.fn(),
        ondelete: vi.fn(),
        onopenGame,
        onopenSync,
      },
    });

    const gameNode = container.querySelector(".node-report");
    await fireEvent.click(gameNode!);
    expect(onopenGame).toHaveBeenCalledWith(10);

    const syncNode = container.querySelector(".node-sync");
    await fireEvent.click(syncNode!);
    expect(onopenSync).toHaveBeenCalledWith(11);
  });
});
