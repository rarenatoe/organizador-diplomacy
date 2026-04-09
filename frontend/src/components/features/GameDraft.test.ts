import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import GameDraft from "./GameDraft.svelte";
import {
  createMockDraftResponse,
  createMockDraftMesa,
  createMockDraftPlayer,
} from "../../tests/fixtures";

// Mock the API module
vi.mock("../../api", () => ({
  fetchGameDraft: vi.fn(),
  saveGameDraft: vi.fn(),
}));

describe("GameDraft.svelte", () => {
  const mockProps = {
    snapshotId: 123,
    onClose: vi.fn(),
    onCancel: vi.fn(),
    onChainUpdate: vi.fn(),
    onOpenGame: vi.fn(),
    onShowError: vi.fn(),
  };

  const mockDraftData = createMockDraftResponse({
    mesas: [
      createMockDraftMesa({
        numero: 1,
        jugadores: [
          createMockDraftPlayer({
            nombre: "Alice",
            es_nuevo: false,
            juegos_ano: 5,
            tiene_prioridad: true,
            partidas_deseadas: 2,
            c_england: 1,
          }),
          createMockDraftPlayer({
            nombre: "Bob",
            es_nuevo: true,
            juegos_ano: 0,
            c_france: 1,
          }),
        ],
      }),
    ],
    tickets_sobrantes: [
      createMockDraftPlayer({
        nombre: "David",
        juegos_ano: 2,
        partidas_deseadas: 2,
        c_germany: 1,
      }),
    ],
    minimo_teorico: 2,
    intentos_usados: 1,
  });

  beforeEach(async () => {
    // Reset any necessary state before each test
    const { fetchGameDraft } = vi.mocked(await import("../../api"));
    fetchGameDraft.mockResolvedValue(mockDraftData);
  });

  it("renders draft data when loaded", async () => {
    const { container } = render(GameDraft, { props: mockProps });

    // Wait a bit for component to render
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Assert structural hierarchy - major content blocks should be wrapped in .section divs
    expect(container.querySelector(".section")).toBeInTheDocument();

    expect(screen.getByText("Partida 1")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("David")).toBeInTheDocument();

    // Verify that experience badges are rendered correctly
    const nuevoTag = screen.getByText("Nuevo");
    const antiguoTag = screen.getByText("Antiguo");

    expect(nuevoTag.closest(".badge")).toBeInTheDocument();
    expect(nuevoTag.closest(".badge")).toHaveClass("warning");
    expect(antiguoTag.closest(".badge")).toBeInTheDocument();
    expect(antiguoTag.closest(".badge")).toHaveClass("success");
  });

  it("shows loading state initially", async () => {
    const { fetchGameDraft } = vi.mocked(await import("../../api"));
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

    // Verify that all experience tags are properly wrapped
    const nuevoTags = screen.getAllByText("Nuevo");
    const antiguoTags = screen.getAllByText("Antiguo");

    nuevoTags.forEach((tag) => {
      expect(tag.closest(".badge")).toBeInTheDocument();
      expect(tag.closest(".badge")).toHaveClass("warning");
    });

    antiguoTags.forEach((tag) => {
      expect(tag.closest(".badge")).toBeInTheDocument();
      expect(tag.closest(".badge")).toHaveClass("success");
    });
  });

  it("saves draft when save button is clicked", async () => {
    const { saveGameDraft } = vi.mocked(await import("../../api"));
    saveGameDraft.mockResolvedValue({ game_id: 456 });

    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Confirmar y Guardar")).toBeInTheDocument();
    });

    const saveButton = screen.getByRole("button", {
      name: /Confirmar y Guardar/i,
    });
    await fireEvent.click(saveButton);

    expect(saveGameDraft).toHaveBeenCalledWith({
      snapshot_id: 123,
      draft: mockDraftData,
      editing_game_id: null,
    });
  });

  it("handles duplicate waitlist users without key warnings", async () => {
    // Create mock draft data with duplicate users in waitlist
    const mockDraftWithDuplicates = createMockDraftResponse({
      mesas: [
        createMockDraftMesa({
          numero: 1,
          jugadores: [
            createMockDraftPlayer({
              nombre: "Alice",
              es_nuevo: false,
              juegos_ano: 5,
              tiene_prioridad: true,
              partidas_deseadas: 2,
              c_england: 1,
            }),
          ],
        }),
      ],
      tickets_sobrantes: [
        createMockDraftPlayer({
          nombre: "DuplicateUser",
          juegos_ano: 2,
          partidas_deseadas: 2,
          c_germany: 1,
        }),
        createMockDraftPlayer({
          nombre: "DuplicateUser", // Same name as above
          juegos_ano: 1,
          partidas_deseadas: 1,
          c_france: 1,
        }),
        createMockDraftPlayer({
          nombre: "DuplicateUser", // Same name again
          juegos_ano: 3,
          partidas_deseadas: 3,
          c_italy: 1,
        }),
      ],
      minimo_teorico: 3,
      intentos_usados: 1,
    });

    const { fetchGameDraft } = vi.mocked(await import("../../api"));
    fetchGameDraft.mockResolvedValue(mockDraftWithDuplicates);

    // Mock console.warn to catch any duplicate key warnings
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    // Render the component with duplicate waitlist users
    render(GameDraft, { props: mockProps });

    // Wait for the component to render
    await vi.waitFor(() => {
      const duplicateUsers = screen.getAllByText("DuplicateUser");
      expect(duplicateUsers).toHaveLength(3);
    });

    // Verify all duplicate users are rendered
    const duplicateUsers = screen.getAllByText("DuplicateUser");
    expect(duplicateUsers).toHaveLength(3);

    // Verify that no duplicate key warnings were thrown
    expect(consoleSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("duplicate key"),
      expect.any(Object),
    );

    // Clean up
    consoleSpy.mockRestore();
  });

  it("shows error when save fails", async () => {
    const { saveGameDraft } = vi.mocked(await import("../../api"));
    saveGameDraft.mockResolvedValue({ game_id: 0, error: "Save failed" });

    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Confirmar y Guardar")).toBeInTheDocument();
    });

    const saveButton = screen.getByRole("button", {
      name: /Confirmar y Guardar/i,
    });
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

    const cancelButton = screen.getByRole("button", { name: /Cancelar/i });
    await fireEvent.click(cancelButton);

    expect(mockProps.onCancel).toHaveBeenCalled();
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
    const { fetchGameDraft } = vi.mocked(await import("../../api"));
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
      const { fetchGameDraft } = vi.mocked(await import("../../api"));
      fetchGameDraft.mockResolvedValue(
        createMockDraftResponse({
          mesas: [
            createMockDraftMesa({
              numero: 1,
              jugadores: [
                createMockDraftPlayer({
                  nombre: "Alice",
                  es_nuevo: false,
                  juegos_ano: 5,
                  tiene_prioridad: true,
                  partidas_deseadas: 2,
                  c_england: 1,
                }),
                createMockDraftPlayer({
                  nombre: "Bob",
                  es_nuevo: true,
                  juegos_ano: 0,
                  c_france: 1,
                }),
              ],
            }),
            createMockDraftMesa({
              numero: 2,
              jugadores: [
                createMockDraftPlayer({
                  nombre: "Charlie",
                  juegos_ano: 3,
                  c_germany: 1,
                }),
              ],
            }),
          ],
          tickets_sobrantes: [
            createMockDraftPlayer({
              nombre: "David",
              juegos_ano: 2,
              partidas_deseadas: 2,
              c_germany: 1,
            }),
          ],
          minimo_teorico: 2,
          intentos_usados: 1,
        }),
      );
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
        const mesa1 = screen.getByText("Partida 1").closest(".card")!;
        const mesa2 = screen.getByText("Partida 2").closest(".card")!;

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
        const mesa1 = screen.getByText("Partida 1").closest(".card")!;
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
      const { fetchGameDraft } = vi.mocked(await import("../../api"));
      fetchGameDraft.mockResolvedValue(
        createMockDraftResponse({
          mesas: [
            createMockDraftMesa({
              numero: 1,
              jugadores: [
                createMockDraftPlayer({
                  nombre: "Alice",
                  juegos_ano: 5,
                  partidas_deseadas: 1,
                }),
              ],
            }),
            createMockDraftMesa({
              numero: 2,
              jugadores: [
                createMockDraftPlayer({
                  // Alice already appears in Mesa 2 — swapping Alice from Mesa 1 here must be blocked.
                  nombre: "Alice",
                  juegos_ano: 5,
                  partidas_deseadas: 1,
                }),
                createMockDraftPlayer({
                  nombre: "Charlie",
                  juegos_ano: 3,
                  partidas_deseadas: 1,
                }),
              ],
            }),
          ],
          minimo_teorico: 2,
          intentos_usados: 1,
        }),
      );

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

  // NEW TESTS FOR EDITING FUNCTIONALITY
  describe("Editing functionality", () => {
    beforeEach(async () => {
      vi.clearAllMocks();
      const { fetchGameDraft } = vi.mocked(await import("../../api"));
      fetchGameDraft.mockResolvedValue(mockDraftData);
    });

    it("uses initialDraft prop and skips fetchGameDraft if provided", async () => {
      const { fetchGameDraft } = vi.mocked(await import("../../api"));

      render(GameDraft, {
        props: {
          ...mockProps,
          initialDraft: mockDraftData,
        },
      });

      // Should not call fetchGameDraft
      expect(fetchGameDraft).not.toHaveBeenCalled();

      // Should immediately render players from the prop
      await vi.waitFor(() => {
        expect(screen.getByText("Partida 1")).toBeInTheDocument();
        expect(screen.getByText("Alice")).toBeInTheDocument();
        expect(screen.getByText("Bob")).toBeInTheDocument();
        expect(screen.getByText("David")).toBeInTheDocument();
      });
    });

    it("passes editing_game_id to saveGameDraft when editing", async () => {
      const { saveGameDraft } = vi.mocked(await import("../../api"));
      saveGameDraft.mockResolvedValue({ game_id: 456 });

      render(GameDraft, {
        props: {
          ...mockProps,
          editingGameId: 99,
        },
      });

      await vi.waitFor(() => {
        expect(screen.getByText("Confirmar y Guardar")).toBeInTheDocument();
      });

      const saveButton = screen.getByText("Confirmar y Guardar");
      await fireEvent.click(saveButton);

      expect(saveGameDraft).toHaveBeenCalledWith({
        snapshot_id: 123,
        draft: mockDraftData,
        editing_game_id: 99,
      });
    });

    it("calls onCancel instead of onClose when editingGameId exists", async () => {
      const { saveGameDraft } = vi.mocked(await import("../../api"));
      saveGameDraft.mockResolvedValue({ game_id: 456 });

      render(GameDraft, {
        props: {
          ...mockProps,
          editingGameId: 456,
        },
      });

      await vi.waitFor(() => {
        expect(screen.getByText("Cancelar")).toBeInTheDocument();
      });

      const cancelButton = screen.getByText("Cancelar");
      await fireEvent.click(cancelButton);

      expect(mockProps.onCancel).toHaveBeenCalled();
    });

    it("calls onCancel when editingGameId is null", async () => {
      const { saveGameDraft } = vi.mocked(await import("../../api"));
      saveGameDraft.mockResolvedValue({ game_id: 456 });

      render(GameDraft, {
        props: {
          ...mockProps,
          editingGameId: null,
        },
      });

      await vi.waitFor(() => {
        expect(screen.getByText("Cancelar")).toBeInTheDocument();
      });

      const cancelButton = screen.getByText("Cancelar");
      await fireEvent.click(cancelButton);

      expect(mockProps.onCancel).toHaveBeenCalled();
    });

    it("handles GM assignment correctly", async () => {
      const { fetchGameDraft } = vi.mocked(await import("../../api"));
      const draftWithGM = createMockDraftResponse({
        ...mockDraftData,
        mesas: [
          createMockDraftMesa({
            numero: 1,
            gm: createMockDraftPlayer({
              nombre: "TestGM",
              juegos_ano: 10,
              partidas_gm: 5,
              c_england: 2,
              c_france: 1,
              c_germany: 1,
              c_italy: 1,
              c_austria: 1,
              c_russia: 1,
              c_turkey: 1,
            }),
            jugadores: mockDraftData.mesas[0]?.jugadores || [],
          }),
        ],
      });
      fetchGameDraft.mockResolvedValue(draftWithGM);

      render(GameDraft, { props: mockProps });

      await vi.waitFor(() => {
        expect(screen.getByText("GM: TestGM")).toBeInTheDocument();
      });
    });
  });

  it("correctly updates country selection including reverting to Aleatorio", async () => {
    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Partida 1")).toBeInTheDocument();
    });

    // Find the country selects
    const countrySelects = document.querySelectorAll(".country-select");
    const aliceSelect = countrySelects[0] as HTMLSelectElement;
    expect(aliceSelect).toBeDefined();

    // Change to England
    await fireEvent.change(aliceSelect, { target: { value: "England" } });
    expect(aliceSelect.value).toBe("England");

    // Change back to Aleatorio (empty string)
    await fireEvent.change(aliceSelect, { target: { value: "" } });
    expect(aliceSelect.value).toBe("");
  });

  it("verifies badge structure for all players", async () => {
    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Partida 1")).toBeInTheDocument();
    });

    // Check that all experience tags are rendered as Badge components
    const nuevoTags = screen.getAllByText("Nuevo");
    const antiguoTags = screen.getAllByText("Antiguo");

    // Test Nuevo badges
    nuevoTags.forEach((tag) => {
      const badge = tag.closest(".badge");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("fixed-width");
      expect(badge).toHaveClass("warning");
    });

    // Test Antiguo badges
    antiguoTags.forEach((tag) => {
      const badge = tag.closest(".badge");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("fixed-width");
      expect(badge).toHaveClass("success");
    });
  });
});
