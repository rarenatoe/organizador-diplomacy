import { render, screen } from "@testing-library/svelte";

import type { GameDraftPlayer } from "../../generated-api";
import PlayerNameTestWrapper from "./PlayerNameTestWrapper.svelte";

describe("PlayerName.svelte", () => {
  type PlayerNameTestPlayer = GameDraftPlayer & {
    notion_id?: string | null;
    notion_name?: string | null;
  };

  const basePlayer: PlayerNameTestPlayer = {
    nombre: "Local Name",
    is_new: true,
    juegos_este_ano: 0,
    has_priority: false,
    partidas_deseadas: 1,
    partidas_gm: 0,
    c_england: 0,
    c_france: 0,
    c_germany: 0,
    c_italy: 0,
    c_austria: 0,
    c_russia: 0,
    c_turkey: 0,
    country: { name: "", reason: "" },
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
    const linkedPlayer: PlayerNameTestPlayer = {
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
    const aliasPlayer: PlayerNameTestPlayer = {
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
    const linkedPlayer: PlayerNameTestPlayer = {
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
    const sameNamePlayer: PlayerNameTestPlayer = {
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
    const nameOnlyLinkedPlayer: PlayerNameTestPlayer = {
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
