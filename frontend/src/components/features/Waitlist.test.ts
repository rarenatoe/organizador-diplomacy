// frontend/src/components/features/Waitlist.test.ts
import { createRawSnippet } from "svelte";
import { describe, expect, it } from "vitest";

import { render, screen } from "@testing-library/svelte";

import { createMockDraftPlayer } from "../../tests/fixtures";
import Waitlist from "./Waitlist.svelte";

describe("Waitlist.svelte", () => {
  const mockPlayers = [
    createMockDraftPlayer({
      nombre: "Player 1",
      cupos_faltantes: 1,
      partidas_deseadas: 2,
    }),
    createMockDraftPlayer({
      nombre: "Player 2",
      cupos_faltantes: null,
      partidas_deseadas: 3,
    }),
  ];

  it("renders players with correct cupos text (handling both API data shapes)", () => {
    render(Waitlist, { props: { players: mockPlayers } });

    expect(screen.getByText("Player 1")).toBeInTheDocument();
    expect(screen.getByText("1 cupo(s)")).toBeInTheDocument(); // Uses cupos_faltantes

    expect(screen.getByText("Player 2")).toBeInTheDocument();
    expect(screen.getByText("3 cupo(s)")).toBeInTheDocument(); // Fallback to partidas_deseadas
  });

  it("applies structural regression guards: unified container and layout shift prevention", () => {
    const { container } = render(Waitlist, { props: { players: mockPlayers } });

    const waitlistContainer = container.querySelector(".waitlist-container");
    expect(waitlistContainer).toBeInTheDocument();

    // Ensure the items are rendered inside the container
    const items = waitlistContainer?.querySelectorAll(".waiting-item");
    expect(items).toHaveLength(2);
  });

  it("renders action snippets and passes the correct index via Svelte 5 snippets", () => {
    const actionSnippetsRendered: number[] = [];

    // Strictly mock a Svelte 5 snippet with arguments
    const mockActions = createRawSnippet((indexFn: () => number) => {
      const idx = indexFn();
      actionSnippetsRendered.push(idx);
      return {
        render: () =>
          `<button data-testid="action-btn-${idx}">Action ${idx}</button>`,
      };
    });

    render(Waitlist, {
      props: {
        players: mockPlayers,
        actions: mockActions,
      },
    });

    expect(screen.getByTestId("action-btn-0")).toBeInTheDocument();
    expect(screen.getByTestId("action-btn-1")).toBeInTheDocument();
    expect(actionSnippetsRendered).toEqual([0, 1]);
  });

  it("applies swapping-active class based on isSwapping callback", () => {
    const { container } = render(Waitlist, {
      props: {
        players: mockPlayers,
        isSwapping: (i: number) => i === 1, // Only second player is swapping
      },
    });

    const items = container.querySelectorAll(".waiting-item");
    expect(items[0]).not.toHaveClass("swapping-active");
    expect(items[1]).toHaveClass("swapping-active");
  });
});
