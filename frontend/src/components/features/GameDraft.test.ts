import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import GameDraft from "./GameDraft.svelte";
import {
  createMockDraftResponse,
  createMockDraftMesa,
  createMockDraftPlayer,
} from "../../tests/fixtures";
import {
  mockSdkSuccess,
  mockSdkError,
  mockApiSuccess,
} from "../../tests/mockHelpers";

// Mock the API module
vi.mock("../../generated-api/sdk.gen", () => ({
  apiGameDraft: vi.fn(),
  apiGameSave: vi.fn(),
  apiChain: vi.fn(),
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
            is_new: false,
            juegos_este_ano: 5,
            has_priority: true,
            partidas_deseadas: 2,
            c_england: 1,
          }),
          createMockDraftPlayer({
            nombre: "Bob",
            is_new: true,
            juegos_este_ano: 0,
            c_france: 1,
          }),
        ],
      }),
    ],
    tickets_sobrantes: [
      createMockDraftPlayer({
        nombre: "David",
        juegos_este_ano: 2,
        partidas_deseadas: 2,
        c_germany: 1,
      }),
    ],
    minimo_teorico: 2,
    intentos_usados: 1,
  });

  beforeEach(async () => {
    // Reset any necessary state before each test
    const { apiGameDraft, apiChain } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    mockSdkSuccess(apiGameDraft, mockDraftData);
    mockSdkSuccess(apiChain, {
      roots: [
        {
          id: 1,
          type: "snapshot",
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          player_count: 0,
          is_latest: false,
          branches: [
            {
              edge: {
                id: 2,
                type: "game",
                created_at: "2024-01-01T00:00:00Z",
                from_id: 1,
                to_id: 2,
              },
              output: {
                id: 2,
                type: "game",
                created_at: "2024-01-01T00:00:00Z",
              },
            },
          ],
        },
      ],
    });
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

    // Verify that is_new badges are rendered correctly
    const nuevoTag = screen.getByText("Nuevo");
    const antiguoTag = screen.getByText("Antiguo");

    expect(nuevoTag.closest(".badge")).toBeInTheDocument();
    expect(nuevoTag.closest(".badge")).toHaveClass("warning");
    expect(antiguoTag.closest(".badge")).toBeInTheDocument();
    expect(antiguoTag.closest(".badge")).toHaveClass("success");
  });

  it("shows loading state initially", async () => {
    const { apiGameDraft } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    apiGameDraft.mockImplementation(() => new Promise<never>(() => {}));

    render(GameDraft, { props: mockProps });

    expect(screen.getByText(/generando draft/i)).toBeInTheDocument();
  });

  it("displays swap buttons for all players", async () => {
    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      const swapButtons = screen.getAllByTitle("Intercambiar");
      expect(swapButtons).toHaveLength(3); // 2 in mesa + 1 in espera
    });

    // Verify that all is_new tags are properly wrapped
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
    const { apiGameSave } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    mockSdkSuccess(apiGameSave, { game_id: 456 });

    render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Confirmar y Guardar")).toBeInTheDocument();
    });

    const saveButton = screen.getByRole("button", {
      name: /Confirmar y Guardar/i,
    });
    await fireEvent.click(saveButton);

    expect(apiGameSave).toHaveBeenCalledWith({
      body: {
        snapshot_id: 123,
        draft: mockDraftData,
        editing_game_id: null,
      },
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
              is_new: false,
              juegos_este_ano: 5,
              has_priority: true,
              partidas_deseadas: 2,
              c_england: 1,
            }),
          ],
        }),
      ],
      tickets_sobrantes: [
        createMockDraftPlayer({
          nombre: "DuplicateUser",
          juegos_este_ano: 2,
          partidas_deseadas: 2,
          c_germany: 1,
        }),
        createMockDraftPlayer({
          nombre: "DuplicateUser", // Same name as above
          juegos_este_ano: 1,
          partidas_deseadas: 1,
          c_france: 1,
        }),
        createMockDraftPlayer({
          nombre: "DuplicateUser", // Same name again
          juegos_este_ano: 3,
          partidas_deseadas: 3,
          c_italy: 1,
        }),
      ],
      minimo_teorico: 3,
      intentos_usados: 1,
    });

    const { apiGameDraft } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    mockSdkSuccess(apiGameDraft, mockDraftWithDuplicates);

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
    const { apiGameSave } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    mockSdkError(apiGameSave, { detail: "Save failed" });

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
    const { apiGameDraft } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    mockSdkError(apiGameDraft, { detail: "Generation failed" });

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
      const { apiGameDraft } = vi.mocked(
        await import("../../generated-api/sdk.gen"),
      );
      mockSdkSuccess(
        apiGameDraft,
        createMockDraftResponse({
          mesas: [
            createMockDraftMesa({
              numero: 1,
              jugadores: [
                createMockDraftPlayer({
                  nombre: "Alice",
                  is_new: false,
                  juegos_este_ano: 5,
                  has_priority: true,
                  partidas_deseadas: 2,
                  c_england: 1,
                }),
                createMockDraftPlayer({
                  nombre: "Bob",
                  is_new: true,
                  juegos_este_ano: 0,
                  c_france: 1,
                }),
              ],
            }),
            createMockDraftMesa({
              numero: 2,
              jugadores: [
                createMockDraftPlayer({
                  nombre: "Charlie",
                  juegos_este_ano: 3,
                  c_germany: 1,
                }),
              ],
            }),
          ],
          tickets_sobrantes: [
            createMockDraftPlayer({
              nombre: "David",
              juegos_este_ano: 2,
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
      if (aliceSwapButton) {
        await fireEvent.click(aliceSwapButton);
      }

      // Click Charlie second (swap execution)
      if (charlieSwapButton) {
        await fireEvent.click(charlieSwapButton);
      }

      // Verify swap occurred - Alice and Charlie should be swapped
      await vi.waitFor(() => {
        const mesa1 = screen.getByText("Partida 1").closest(".card");
        const mesa2 = screen.getByText("Partida 2").closest(".card");
        if (mesa1 && mesa2) {
          // Alice should now be in Mesa 2, Charlie in Mesa 1
          expect(mesa1.textContent).toContain("Charlie");
          expect(mesa2.textContent).toContain("Alice");
        }
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
      if (aliceSwapButton) {
        await fireEvent.click(aliceSwapButton);
      }
      if (davidSwapButton) {
        await fireEvent.click(davidSwapButton);
      }

      // Verify swap occurred
      await vi.waitFor(() => {
        const mesa1 = screen.getByText("Partida 1").closest(".card");
        const waitingSection = screen
          .getByText("Lista de espera")
          .closest(".section");
        if (mesa1 && waitingSection) {
          // Alice should be in waiting list, David should be in Mesa 1
          expect(mesa1.textContent).toContain("David");
          expect(waitingSection.textContent).toContain("Alice");
        }
      });
    });

    it("constraint validation prevents duplicate players in same mesa", async () => {
      // Use a special draft where Mesa 2 already contains a player named "Alice"
      // so swapping Alice from Mesa 1 into Mesa 2 triggers the duplicate check.
      const { apiGameDraft } = vi.mocked(
        await import("../../generated-api/sdk.gen"),
      );
      mockSdkSuccess(
        apiGameDraft,
        createMockDraftResponse({
          mesas: [
            createMockDraftMesa({
              numero: 1,
              jugadores: [
                createMockDraftPlayer({
                  nombre: "Alice",
                  juegos_este_ano: 5,
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
                  juegos_este_ano: 5,
                  partidas_deseadas: 1,
                }),
                createMockDraftPlayer({
                  nombre: "Charlie",
                  juegos_este_ano: 3,
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
      const aliceInMesa1 = swapButtons[0];
      const charlieInMesa2 = swapButtons[2];
      if (aliceInMesa1 && charlieInMesa2) {
        await fireEvent.click(aliceInMesa1);
        await fireEvent.click(charlieInMesa2);
      }

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
      const { apiGameDraft } = vi.mocked(
        await import("../../generated-api/sdk.gen"),
      );
      mockSdkSuccess(apiGameDraft, mockDraftData);
    });

    it("uses initialDraft prop and skips fetchGameDraft if provided", async () => {
      const { apiGameDraft } = vi.mocked(
        await import("../../generated-api/sdk.gen"),
      );

      render(GameDraft, {
        props: {
          ...mockProps,
          initialDraft: mockDraftData,
        },
      });

      // Should not call fetchGameDraft
      expect(apiGameDraft).not.toHaveBeenCalled();

      // Should immediately render players from the prop
      await vi.waitFor(() => {
        expect(screen.getByText("Partida 1")).toBeInTheDocument();
        expect(screen.getByText("Alice")).toBeInTheDocument();
        expect(screen.getByText("Bob")).toBeInTheDocument();
        expect(screen.getByText("David")).toBeInTheDocument();
      });
    });

    it("passes editing_game_id to saveGameDraft when editing", async () => {
      const { apiGameSave } = vi.mocked(
        await import("../../generated-api/sdk.gen"),
      );
      mockSdkSuccess(apiGameSave, { game_id: 456 });

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

      expect(apiGameSave).toHaveBeenCalledWith({
        body: {
          snapshot_id: 123,
          draft: mockDraftData,
          editing_game_id: 99,
        },
      });
    });

    it("calls onCancel instead of onClose when editingGameId exists", async () => {
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
      const { apiGameDraft } = vi.mocked(
        await import("../../generated-api/sdk.gen"),
      );
      const draftWithGM = createMockDraftResponse({
        ...mockDraftData,
        mesas: [
          createMockDraftMesa({
            numero: 1,
            gm: createMockDraftPlayer({
              nombre: "TestGM",
              juegos_este_ano: 10,
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
      mockSdkSuccess(apiGameDraft, draftWithGM);

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

    // Check that all is_new tags are rendered as Badge components
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

  it("renders tabular grid layout with separated select and tooltip cells to prevent layout shift", async () => {
    const { tick } = await import("svelte");
    const { apiGameDraft } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );

    // Add a reason to first player so tooltip renders
    const modifiedDraft = JSON.parse(
      JSON.stringify(mockDraftData),
    ) as typeof mockDraftData;
    if (modifiedDraft.mesas[0]?.jugadores[0]) {
      modifiedDraft.mesas[0].jugadores[0].country = {
        name: "France",
        reason: "Test Reason",
      };
    }

    apiGameDraft.mockResolvedValueOnce(mockApiSuccess(modifiedDraft) as never);

    render(GameDraft, { props: mockProps });

    await tick();
    await new Promise((r) => setTimeout(r, 0));
    await tick();

    // Verify select and tooltip are not wrapped together
    const selects = document.querySelectorAll(".country-select");
    expect(selects.length).toBeGreaterThan(0);

    const firstSelect = selects[0];
    const parentRow = firstSelect?.closest("li");
    if (firstSelect && parentRow) {
      // Verify grid structure classes
      expect(parentRow.querySelector(".tooltip-cell")).toBeInTheDocument();

      // The select should be a direct child of row, NOT inside a flex container with tooltip
      expect(firstSelect.parentElement).toBe(parentRow);
    }
  });

  it("swaps country.reason along with the country during a player swap", async () => {
    const { apiGameDraft } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    const draftData = createMockDraftResponse({
      mesas: [
        createMockDraftMesa({
          numero: 1,
          jugadores: [
            createMockDraftPlayer({
              nombre: "Player A",
              country: { name: "France", reason: "Algorithm says so" },
            }),
            createMockDraftPlayer({
              nombre: "Player B",
              country: { name: "Germany", reason: "" },
            }), // No reason
          ],
        }),
      ],
    });
    mockSdkSuccess(apiGameDraft, draftData);

    render(GameDraft, { props: mockProps });
    await vi.waitFor(() =>
      expect(screen.getByText("Player A")).toBeInTheDocument(),
    );

    const swapButtons = screen.getAllByTitle("Intercambiar");
    const buttonA = swapButtons[0];
    const buttonB = swapButtons[1];
    if (buttonA && buttonB) {
      await fireEvent.click(buttonA); // Click Player A
      await fireEvent.click(buttonB); // Click Player B
    }

    await vi.waitFor(() => {
      // Player B should now be in slot 1 and inherited the tooltip
      const rows = document.querySelectorAll(".player-list li");
      const row1 = rows[0];
      const row2 = rows[1];
      if (row1 && row2) {
        expect(row1.textContent).toContain("Player B");
        expect(row1.querySelector(".tooltip-cell")).not.toBeEmptyDOMElement();

        expect(row2.textContent).toContain("Player A");
        expect(row2.querySelector(".tooltip-cell")).toBeEmptyDOMElement();
      }
    });
  });

  it("swaps country reason when manually changing dropdown causes a conflict", async () => {
    const { apiGameDraft } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    const { tick } = await import("svelte");
    const draftData = createMockDraftResponse({
      mesas: [
        createMockDraftMesa({
          numero: 1,
          jugadores: [
            createMockDraftPlayer({
              nombre: "Player A",
              country: { name: "France", reason: "Reason A" },
            }),
            createMockDraftPlayer({
              nombre: "Player B",
              country: { name: "Germany", reason: "Reason B" },
            }),
          ],
        }),
      ],
    });
    mockSdkSuccess(apiGameDraft, draftData);

    render(GameDraft, { props: mockProps });
    await vi.waitFor(() =>
      expect(screen.getByText("Player A")).toBeInTheDocument(),
    );

    const selects = document.querySelectorAll(".country-select");
    const selectA = selects[0];
    if (selectA) {
      // Player A steals Germany (currently held by Player B)
      await fireEvent.change(selectA, { target: { value: "Germany" } });
    }

    await vi.waitFor(() => {
      const rows = document.querySelectorAll(".player-list li");
      const row1 = rows[0]; // Player A
      const row2 = rows[1]; // Player B
      if (row1 && row2) {
        expect(row1.querySelector(".country-select")).toHaveValue("Germany");
        expect(row2.querySelector(".country-select")).toHaveValue("France");
      }
    });

    // Hover over Player A's new tooltip to verify they inherited "Reason B"
    const rowsAgain = document.querySelectorAll(".player-list li");
    const tooltipA = rowsAgain[0]?.querySelector(".tooltip-trigger");
    if (tooltipA) {
      await fireEvent.mouseEnter(tooltipA);
      await tick();
    }

    expect(document.body.querySelector(".tooltip-popover")).toHaveTextContent(
      "Reason B",
    );
  });

  it("clears country.reason when manually changing the country dropdown", async () => {
    const { apiGameDraft } = vi.mocked(
      await import("../../generated-api/sdk.gen"),
    );
    const draftData = createMockDraftResponse({
      mesas: [
        createMockDraftMesa({
          numero: 1,
          jugadores: [
            createMockDraftPlayer({
              nombre: "Player C",
              country: { name: "France", reason: "Manual override test" },
            }),
          ],
        }),
      ],
    });
    mockSdkSuccess(apiGameDraft, draftData);

    render(GameDraft, { props: mockProps });
    await vi.waitFor(() =>
      expect(screen.getByText("Player C")).toBeInTheDocument(),
    );

    const row = document.querySelector(".player-list li");
    expect(row).toBeDefined();
    if (row) {
      expect(row.querySelector(".tooltip-cell")).not.toBeEmptyDOMElement();

      const select = row.querySelector(".country-select") as HTMLSelectElement;
      await fireEvent.change(select, { target: { value: "Germany" } });

      await vi.waitFor(() => {
        expect(select.value).toBe("Germany");
        // Tooltip should be destroyed since the algorithm was overridden
        expect(row.querySelector(".tooltip-cell")).toBeEmptyDOMElement();
      });
    }
  });

  it("enforces structural regression guard: uses centralized Waitlist component", async () => {
    const { container } = render(GameDraft, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Partida 1")).toBeInTheDocument();
    });

    // Verify it uses the waitlist-container abstraction to govern spacing
    // If someone decouples the interactive list from the read-only list, this test will fail
    expect(container.querySelector(".waitlist-container")).toBeInTheDocument();
  });
});
