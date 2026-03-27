import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import GameDraft from "./GameDraft.svelte";
import "@testing-library/jest-dom";

// Mock the API module
vi.mock("../api", () => ({
  fetchGameDraft: vi.fn(),
  saveGameDraft: vi.fn(),
}));

// Mock the stores module
vi.mock("../stores.svelte", () => ({
  setActiveNodeId: vi.fn(),
}));

// Mock the snapshotUtils module
vi.mock("../snapshotUtils", () => ({
  findLatestGameId: vi.fn(),
}));

describe("GameDraft.svelte", () => {
  const mockProps = {
    snapshotId: 123,
    onClose: vi.fn(),
    onChainUpdate: vi.fn(),
    onOpenGame: vi.fn(),
    onShowError: vi.fn(),
  };

  const mockDraftData = {
    mesas: [
      {
        numero: 1,
        gm: null,
        jugadores: [
          {
            nombre: "Alice",
            etiqueta: "A5",
            es_nuevo: false,
            juegos_ano: 5,
            tiene_prioridad: true,
            partidas_deseadas: 2,
            partidas_gm: 0,
            c_england: 1,
            c_france: 0,
            c_germany: 0,
            c_italy: 0,
            c_austria: 0,
            c_russia: 0,
            c_turkey: 0,
          },
          {
            nombre: "Bob",
            etiqueta: "B0",
            es_nuevo: true,
            juegos_ano: 0,
            tiene_prioridad: false,
            partidas_deseadas: 1,
            partidas_gm: 0,
            c_england: 0,
            c_france: 1,
            c_germany: 0,
            c_italy: 0,
            c_austria: 0,
            c_russia: 0,
            c_turkey: 0,
          },
        ],
      },
    ],
    tickets_sobrantes: [
      {
        nombre: "David",
        etiqueta: "D2",
        es_nuevo: false,
        juegos_ano: 2,
        tiene_prioridad: false,
        partidas_deseadas: 2,
        partidas_gm: 0,
        c_england: 0,
        c_france: 0,
        c_germany: 1,
        c_italy: 0,
        c_austria: 0,
        c_russia: 0,
        c_turkey: 0,
      },
    ],
    minimo_teorico: 2,
    intentos_usados: 1,
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    const { fetchGameDraft } = vi.mocked(await import("../api"));
    fetchGameDraft.mockResolvedValue(mockDraftData);
  });

  it("renders draft data when loaded", async () => {
    render(GameDraft, { props: mockProps });

    // Wait for loading to complete
    await vi.waitFor(() => {
      expect(screen.getByText("Partida 1")).toBeInTheDocument();
      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
      expect(screen.getByText("David")).toBeInTheDocument();
    });
  });

  it("shows loading state initially", async () => {
    const { fetchGameDraft } = vi.mocked(await import("../api"));
    fetchGameDraft.mockImplementation(() => new Promise(() => {}));

    render(GameDraft, { props: mockProps });

    expect(screen.getByText(/generando draft/i)).toBeInTheDocument();
  });

  it("displays swap buttons for all players", async () => {
    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      const swapButtons = screen.getAllByTitle("Intercambiar");
      expect(swapButtons).toHaveLength(3); // 2 in mesa + 1 in espera
    });
  });

  it("saves draft when save button is clicked", async () => {
    const { saveGameDraft } = vi.mocked(await import("../api"));
    saveGameDraft.mockResolvedValue({ game_id: 456 });

    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("✨ Confirmar y Guardar")).toBeInTheDocument();
    });

    const saveButton = screen.getByText("✨ Confirmar y Guardar");
    await fireEvent.click(saveButton);

    expect(saveGameDraft).toHaveBeenCalledWith(123, mockDraftData);
  });

  it("shows error when save fails", async () => {
    const { saveGameDraft } = vi.mocked(await import("../api"));
    saveGameDraft.mockResolvedValue({ game_id: 0, error: "Save failed" });

    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("✨ Confirmar y Guardar")).toBeInTheDocument();
    });

    const saveButton = screen.getByText("✨ Confirmar y Guardar");
    await fireEvent.click(saveButton);

    await vi.waitFor(() => {
      expect(mockProps.onShowError).toHaveBeenCalledWith(
        "Error al guardar draft",
        "Save failed",
      );
    });
  });

  it("closes modal when cancel button is clicked", async () => {
    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Cancelar")).toBeInTheDocument();
    });

    const cancelButton = screen.getByText("Cancelar");
    await fireEvent.click(cancelButton);

    expect(mockProps.onClose).toHaveBeenCalled();
  });

  it("shows intentos_usados information", async () => {
    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Intentos usados")).toBeInTheDocument();
      // Find the meta-grid and check it contains the value 1
      const metaGrid = screen
        .getByText("Intentos usados")
        .closest(".meta-grid");
      expect(metaGrid).toHaveTextContent("1");
    });
  });

  it("shows error when draft generation fails", async () => {
    const { fetchGameDraft } = vi.mocked(await import("../api"));
    fetchGameDraft.mockResolvedValue({
      mesas: [],
      tickets_sobrantes: [],
      minimo_teorico: 0,
      intentos_usados: 0,
      error: "Generation failed",
    });

    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(mockProps.onShowError).toHaveBeenCalledWith(
        "Error al generar draft",
        "Generation failed",
      );
    });
  });

  describe("handlePlayerClick swap functionality", () => {
    beforeEach(async () => {
      vi.clearAllMocks();
      const { fetchGameDraft } = vi.mocked(await import("../api"));
      fetchGameDraft.mockResolvedValue({
        mesas: [
          {
            numero: 1,
            gm: null,
            jugadores: [
              {
                nombre: "Alice",
                es_nuevo: false,
                juegos_ano: 5,
                tiene_prioridad: true,
                partidas_deseadas: 2,
                partidas_gm: 0,
                c_england: 1,
                c_france: 0,
                c_germany: 0,
                c_italy: 0,
                c_austria: 0,
                c_russia: 0,
                c_turkey: 0,
              },
              {
                nombre: "Bob",
                es_nuevo: true,
                juegos_ano: 0,
                tiene_prioridad: false,
                partidas_deseadas: 1,
                partidas_gm: 0,
                c_england: 0,
                c_france: 1,
                c_germany: 0,
                c_italy: 0,
                c_austria: 0,
                c_russia: 0,
                c_turkey: 0,
              },
            ],
          },
          {
            numero: 2,
            gm: null,
            jugadores: [
              {
                nombre: "Charlie",
                es_nuevo: false,
                juegos_ano: 3,
                tiene_prioridad: false,
                partidas_deseadas: 1,
                partidas_gm: 0,
                c_england: 0,
                c_france: 0,
                c_germany: 1,
                c_italy: 0,
                c_austria: 0,
                c_russia: 0,
                c_turkey: 0,
              },
            ],
          },
        ],
        tickets_sobrantes: [
          {
            nombre: "David",
            es_nuevo: false,
            juegos_ano: 2,
            tiene_prioridad: false,
            partidas_deseadas: 2,
            partidas_gm: 0,
            c_england: 0,
            c_france: 0,
            c_germany: 1,
            c_italy: 0,
            c_austria: 0,
            c_russia: 0,
            c_turkey: 0,
          },
        ],
        minimo_teorico: 2,
        intentos_usados: 1,
      });
    });

    it("valid swap between mesa players", async () => {
      render(GameDraft, { props: mockProps });

      // Wait for component to load
      await vi.waitFor(() => {
        expect(screen.getByText("Partida 1")).toBeInTheDocument();
        expect(screen.getByText("Partida 2")).toBeInTheDocument();
      });

      // Get swap buttons for Alice (Mesa 1) and Charlie (Mesa 2)
      const swapButtons = screen.getAllByTitle("Intercambiar");
      const aliceSwapButton = swapButtons.find((btn) => {
        const li = btn.closest("li");
        return li !== null && li.textContent.includes("Alice");
      });
      const charlieSwapButton = swapButtons.find((btn) => {
        const li = btn.closest("li");
        return li !== null && li.textContent.includes("Charlie");
      });

      // Click Alice first (first selection)
      await fireEvent.click(aliceSwapButton!);

      // Click Charlie second (swap execution)
      await fireEvent.click(charlieSwapButton!);

      // Verify swap occurred - Alice and Charlie should be swapped
      await vi.waitFor(() => {
        const mesa1 = screen.getByText("Partida 1").closest(".mesa-card")!;
        const mesa2 = screen.getByText("Partida 2").closest(".mesa-card")!;

        // Alice should now be in Mesa 2, Charlie in Mesa 1
        expect(mesa1.textContent).toContain("Charlie");
        expect(mesa2.textContent).toContain("Alice");
      });
    });

    it("waitlist to mesa swap", async () => {
      render(GameDraft, { props: mockProps });

      await vi.waitFor(() => {
        expect(screen.getByText("Partida 1")).toBeInTheDocument();
        expect(screen.getByText("David")).toBeInTheDocument(); // David is in waiting list
      });

      const swapButtons = screen.getAllByTitle("Intercambiar");
      const aliceSwapButton = swapButtons.find((btn) => {
        const li = btn.closest("li");
        return li !== null && li.textContent.includes("Alice");
      });
      const davidSwapButton = swapButtons.find((btn) => {
        const div = btn.closest("div");
        return div !== null && div.textContent.includes("David"); // David is in waiting list
      });

      // Click Alice first, then David (swap execution)
      await fireEvent.click(aliceSwapButton!);
      await fireEvent.click(davidSwapButton!);

      // Verify swap occurred
      await vi.waitFor(() => {
        const mesa1 = screen.getByText("Partida 1").closest(".mesa-card")!;
        const waitingSection = screen
          .getByText("Lista de espera")
          .closest(".section")!;

        // Alice should be in waiting list, David should be in Mesa 1
        expect(mesa1.textContent).toContain("David");
        expect(waitingSection.textContent).toContain("Alice");
      });
    });

    it("constraint validation prevents duplicate players in same mesa", async () => {
      // Use a special draft where Mesa 2 already contains a player named "Alice"
      // so swapping Alice from Mesa 1 into Mesa 2 triggers the duplicate check.
      const { fetchGameDraft } = vi.mocked(await import("../api"));
      fetchGameDraft.mockResolvedValue({
        mesas: [
          {
            numero: 1,
            gm: null,
            jugadores: [
              {
                nombre: "Alice",
                es_nuevo: false,
                juegos_ano: 5,
                tiene_prioridad: false,
                partidas_deseadas: 1,
                partidas_gm: 0,
                c_england: 0,
                c_france: 0,
                c_germany: 0,
                c_italy: 0,
                c_austria: 0,
                c_russia: 0,
                c_turkey: 0,
              },
            ],
          },
          {
            numero: 2,
            gm: null,
            jugadores: [
              {
                // Alice already appears in Mesa 2 — swapping Alice from Mesa 1 here must be blocked.
                nombre: "Alice",
                es_nuevo: false,
                juegos_ano: 5,
                tiene_prioridad: false,
                partidas_deseadas: 1,
                partidas_gm: 0,
                c_england: 0,
                c_france: 0,
                c_germany: 0,
                c_italy: 0,
                c_austria: 0,
                c_russia: 0,
                c_turkey: 0,
              },
              {
                nombre: "Charlie",
                es_nuevo: false,
                juegos_ano: 3,
                tiene_prioridad: false,
                partidas_deseadas: 1,
                partidas_gm: 0,
                c_england: 0,
                c_france: 0,
                c_germany: 0,
                c_italy: 0,
                c_austria: 0,
                c_russia: 0,
                c_turkey: 0,
              },
            ],
          },
        ],
        tickets_sobrantes: [],
        minimo_teorico: 2,
        intentos_usados: 1,
      });

      render(GameDraft, { props: mockProps });

      await vi.waitFor(() => {
        expect(screen.getByText("Partida 1")).toBeInTheDocument();
        expect(screen.getByText("Partida 2")).toBeInTheDocument();
      });

      // Select Alice from Mesa 1 (first swap button)
      const swapButtons = screen.getAllByTitle("Intercambiar");
      // Alice in Mesa 1 is the first button; Charlie in Mesa 2 is the third
      const aliceInMesa1 = swapButtons[0]!;
      const charlieInMesa2 = swapButtons[2]!;

      await fireEvent.click(aliceInMesa1);
      await fireEvent.click(charlieInMesa2);

      // Constraint: Alice is already in Mesa 2, so the swap must be blocked
      await vi.waitFor(() => {
        expect(mockProps.onShowError).toHaveBeenCalledWith(
          "Movimiento Inválido",
          expect.stringContaining("Alice"),
        );
      });
    });
  });
});
