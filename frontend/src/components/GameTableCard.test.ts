import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import GameTableCard from "./GameTableCard.svelte";

describe("GameTableCard", () => {
  it("renders the table number in the title correctly", () => {
    render(GameTableCard, {
      props: {
        tableNumber: 1,
        gmName: null,
      },
    });

    expect(screen.getByText("Partida 1")).toBeInTheDocument();
  });

  it("renders GM badge when gmName is provided", () => {
    render(GameTableCard, {
      props: {
        tableNumber: 2,
        gmName: "Alice",
      },
    });

    expect(screen.getByText("GM: Alice")).toBeInTheDocument();
  });

  it("renders missing GM badge when gmName is null", () => {
    render(GameTableCard, {
      props: {
        tableNumber: 3,
        gmName: null,
      },
    });

    expect(screen.getByText("⚠️ Sin GM")).toBeInTheDocument();
  });

  it("has correct CSS classes and structure", () => {
    const { container } = render(GameTableCard, {
      props: {
        tableNumber: 1,
        gmName: "Alice",
      },
    });

    const card = container.querySelector(".card");
    const cardHeader = container.querySelector(".card-header");
    const cardTitle = container.querySelector(".card-title");

    expect(card).toBeInTheDocument();
    expect(cardHeader).toBeInTheDocument();
    expect(cardTitle).toBeInTheDocument();
    expect(cardTitle).toHaveTextContent("Partida 1");
  });
});
