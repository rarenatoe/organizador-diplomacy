import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import type { EditPlayerRow } from "../../types";
import PlayerNameTestWrapper from "./PlayerNameTestWrapper.svelte";

describe("PlayerName.svelte", () => {
  const basePlayer: EditPlayerRow = {
    nombre: "Local Name",
    experiencia: "Nuevo",
    juegos_este_ano: 0,
    prioridad: 0,
    partidas_deseadas: 1,
    partidas_gm: 0,
  };

  it("renders just the name when not linked (read-only)", () => {
    render(PlayerNameTestWrapper, {
      props: { player: basePlayer, editable: false },
    });
    expect(screen.getByText("Local Name")).toBeInTheDocument();
    expect(screen.queryByText("⚡️")).toBeNull();
  });

  it("renders an input when editable", () => {
    render(PlayerNameTestWrapper, {
      props: { player: basePlayer, editable: true },
    });
    expect(screen.getByDisplayValue("Local Name")).toBeInTheDocument();
    expect(screen.queryByText("⚡️")).toBeNull();
  });

  it("renders ⚡️ icon when notion_id is present", () => {
    const linkedPlayer: EditPlayerRow = {
      ...basePlayer,
      notion_id: "123",
      notion_name: "Local Name",
    };
    render(PlayerNameTestWrapper, {
      props: { player: linkedPlayer, editable: false },
    });
    expect(screen.getByText("Local Name")).toBeInTheDocument();
    expect(screen.getByText("⚡️")).toBeInTheDocument();
  });

  it("renders alias hint when notion_name differs from nombre", () => {
    const aliasPlayer: EditPlayerRow = {
      ...basePlayer,
      notion_id: "123",
      notion_name: "Notion Name",
    };
    render(PlayerNameTestWrapper, {
      props: { player: aliasPlayer, editable: false },
    });
    expect(screen.getByText("Local Name")).toBeInTheDocument();
    expect(screen.getByText("(Notion Name)")).toBeInTheDocument();
    expect(screen.getByText("⚡️")).toBeInTheDocument();
  });

  it("hides ⚡️ icon if showNotionIndicator is false", () => {
    const linkedPlayer: EditPlayerRow = {
      ...basePlayer,
      notion_id: "123",
      notion_name: "Local Name",
    };
    render(PlayerNameTestWrapper, {
      props: {
        player: linkedPlayer,
        editable: false,
        showNotionIndicator: false,
      },
    });
    expect(screen.queryByText("⚡️")).toBeNull();
  });

  it("hides alias hint when notion_name normalizes to the same string as nombre", () => {
    // Different casing and whitespace, but normalizes to the same identity
    const sameNamePlayer: EditPlayerRow = {
      ...basePlayer,
      nombre: "Local Name",
      notion_id: "123",
      notion_name: "  local name  ",
    };
    render(PlayerNameTestWrapper, {
      props: { player: sameNamePlayer, editable: false },
    });

    expect(screen.getByText("Local Name")).toBeInTheDocument();
    // Alias should NOT render because they are practically the same name
    expect(screen.queryByText("(local name)")).toBeNull();
    expect(screen.getByText("⚡️")).toBeInTheDocument();
  });

  it("renders ⚡️ icon when only notion_name is present (no notion_id)", () => {
    const nameOnlyLinkedPlayer: EditPlayerRow = {
      ...basePlayer,
      notion_id: null,
      notion_name: "Notion Name",
    };
    render(PlayerNameTestWrapper, {
      props: { player: nameOnlyLinkedPlayer, editable: false },
    });

    expect(screen.getByText("Local Name")).toBeInTheDocument();
    expect(screen.getByText("(Notion Name)")).toBeInTheDocument();
    // Icon MUST still render because notion_name acts as a valid link indicator
    expect(screen.getByText("⚡️")).toBeInTheDocument();
  });

  it("maintains correct DOM structure for flexbox layout (regression guard)", () => {
    const linkedPlayer = {
      ...basePlayer,
      notion_id: "123",
      notion_name: "Notion Name",
    };

    const { container } = render(PlayerNameTestWrapper, {
      props: { player: linkedPlayer, editable: true },
    });

    const wrapper = container.querySelector(".player-name-wrapper");
    expect(wrapper).toBeInTheDocument();

    // The name element (wrapper for the input) MUST have the name-element class for flex: 1
    const nameElement = container.querySelector(".name-element");
    expect(nameElement).toBeInTheDocument();

    // The tooltip/icon should be a sibling of the name-element
    const icon = screen.getByText("⚡️");
    expect(icon.closest(".tooltip-trigger")).toBeInTheDocument();
    expect(icon.closest(".tooltip-trigger")?.parentElement).toBe(wrapper);
  });
});
