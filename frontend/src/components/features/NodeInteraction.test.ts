import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import GameNode from "./GameNode.svelte";
import { setActiveNodeId } from "../../stores.svelte";

describe("Node Interaction Seatbelts", () => {
  beforeEach(() => {
    setActiveNodeId(null);
  });

  it("GameNode triggers onOpen with correct ID when clicked", async () => {
    const onOpen = vi.fn();
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
        onOpen,
      },
    });

    const nodeDiv = container.querySelector(".node-report");
    expect(nodeDiv).not.toBeNull();
    await fireEvent.click(nodeDiv!);

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(42);
  });

  it("GameNode has active class when activeNodeId matches", () => {
    setActiveNodeId(42);
    const onOpen = vi.fn();
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
        onOpen,
      },
    });

    const nodeDiv = container.querySelector(".node-report");
    expect(nodeDiv).not.toBeNull();
    expect(nodeDiv!.classList.contains("active")).toBe(true);
  });

  it("GameNode does not have active class when activeNodeId does not match", () => {
    setActiveNodeId(99);
    const onOpen = vi.fn();
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
        onOpen,
      },
    });

    const nodeDiv = container.querySelector(".node-report");
    expect(nodeDiv).not.toBeNull();
    expect(nodeDiv!.classList.contains("active")).toBe(false);
  });

  it("GameNode does not have active class when activeNodeId is null", () => {
    setActiveNodeId(null);
    const onOpen = vi.fn();
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
        onOpen,
      },
    });

    const nodeDiv = container.querySelector(".node-report");
    expect(nodeDiv).not.toBeNull();
    expect(nodeDiv!.classList.contains("active")).toBe(false);
  });
});
