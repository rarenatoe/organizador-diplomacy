import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import CardGridTestWrapper from "./CardGridTestWrapper.test.svelte";

describe("CardGrid Layout Components", () => {
  it("renders children successfully within the grid and grid-item wrappers", () => {
    const { container } = render(CardGridTestWrapper);

    const grid = container.querySelector(".card-grid-container");
    expect(grid).toBeInTheDocument();

    const item = container.querySelector(".card-grid-item");
    expect(item).toBeInTheDocument();

    expect(container.textContent).toContain("Mock Card Content");
  });
});
