import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import GameNode from "./GameNode.svelte";

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
});
