import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import GameDetail from "./GameDetail.svelte";
import { tick } from "svelte";
import * as generatedApi from "../../generated-api";
import { mockApiSuccess } from "../../tests/mockHelpers";
import { createMockDraftPlayer } from "../../tests/fixtures";
import type { GameDetailResponse } from "../../generated-api";

const apiGameSpy = vi.spyOn(generatedApi, "apiGame");

const defaultGameData: GameDetailResponse = {
  id: 1,
  created_at: "2024-01-01T00:00:00Z",
  intentos: 3,
  input_snapshot_id: 10,
  output_snapshot_id: 20,
  mesas: [
    {
      numero: 1,
      gm: createMockDraftPlayer({ nombre: "GameMaster1" }),
      jugadores: [
        createMockDraftPlayer({
          nombre: "Alice",
          is_new: true,
          country: { name: "England", reason: "Algorithm says so" },
        }),
        createMockDraftPlayer({
          nombre: "Bob",
          is_new: false,
          country: { name: "France", reason: "" },
        }),
      ],
    },
  ],
  waiting_list: [
    createMockDraftPlayer({ nombre: "Charlie", cupos_faltantes: 1 }),
    createMockDraftPlayer({ nombre: "Diana", cupos_faltantes: 1 }),
  ],
};

// Mock the utils module
vi.mock("../../utils", () => ({
  esc: vi.fn((s: string | null | undefined) => s ?? ""),
  normalizeName: vi.fn((name: string) => name.toLowerCase().trim()),
}));

// Mock navigator.clipboard
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.defineProperty(navigator, "clipboard", {
  value: mockClipboard,
  writable: true,
});

describe("GameDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    apiGameSpy.mockResolvedValue(mockApiSuccess(defaultGameData));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders game details with mesas and waiting list", async () => {
    const { container } = render(GameDetail, {
      props: {
        id: 1,
        onOpenGameDraft: vi.fn(),
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Assert structural hierarchy - major content blocks should be wrapped in .section divs
    expect(container.querySelector(".section")).toBeInTheDocument();

    // Verify game info is displayed
    expect(screen.getByText(/Resumen/)).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy(); // intentos

    // Verify mesas are displayed
    expect(screen.getByText("Partida 1")).toBeTruthy();
    expect(screen.getByText("GM: GameMaster1")).toBeTruthy();
    expect(screen.getByText("Alice")).toBeTruthy();
    expect(screen.getByText(/🇬🇧/)).toBeTruthy();
    expect(screen.getByText("Bob")).toBeTruthy();
    expect(screen.getByText(/🇫🇷/)).toBeTruthy();

    // Verify waiting list is displayed
    expect(screen.getByText("Lista de espera")).toBeTruthy();
    expect(screen.getByText("Charlie")).toBeTruthy();
    expect(screen.getByText("Diana")).toBeTruthy();

    // Verify that is_new badges are rendered correctly
    const nuevoTag = screen.getByText("Nuevo");
    const antiguoTag = screen.getByText("Antiguo");

    expect(nuevoTag.closest(".badge")).toBeInTheDocument();
    expect(nuevoTag.closest(".badge")).toHaveClass("warning");
    expect(antiguoTag.closest(".badge")).toBeInTheDocument();
    expect(antiguoTag.closest(".badge")).toHaveClass("success");
  });

  it("copies share list and shows feedback when share button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
        onOpenGameDraft: vi.fn(),
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Find the share copy button
    const shareButton = screen.getByRole("button", {
      name: /Copiar lista para compartir/i,
    });
    await fireEvent.click(shareButton);

    // Verify clipboard.writeText was called
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);

    // Verify the generated text contains expected content
    const clipboardText = mockClipboard.writeText.mock.calls[0]?.[0] as string;
    expect(clipboardText).toContain("Partida 1");
    expect(clipboardText).toContain("GM: GameMaster1");
    expect(clipboardText).toContain("- Alice (Inglaterra)");
    expect(clipboardText).toContain("- Bob (Francia)");
    expect(clipboardText).toContain("Lista de espera:");
    expect(clipboardText).toContain("- Charlie (1 cupos)");
    expect(clipboardText).toContain("- Diana (1 cupos)");

    // Verify button text changes to "Copiado"
    expect(screen.getByText("Copiado")).toBeTruthy();

    // Verify button has success variant when copied
    expect(shareButton.classList.contains("btn-success")).toBe(true);

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Copiar lista para compartir/i }),
      ).toBeTruthy();
    });
  });

  it("copies players list and shows feedback when players button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
        onOpenGameDraft: vi.fn(),
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Find the players copy button
    const playersButton = screen.getByRole("button", {
      name: /Copiar jugadores/i,
    });
    await fireEvent.click(playersButton);

    // Verify clipboard.writeText was called with seat numbering and translated countries
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      "1. Alice (Inglaterra*)\n2. Bob (Francia)\n\n* Algorithm says so",
    );

    // Verify button text changes to "Copiado"
    expect(screen.getByText("Copiado")).toBeTruthy();

    // Verify button has success variant when copied
    expect(playersButton.classList.contains("btn-success")).toBe(true);

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Copiar jugadores/i }),
      ).toBeTruthy();
    });
  });

  it("copies waiting list and shows feedback when waiting button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
        onOpenGameDraft: vi.fn(),
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Find the waiting list copy button
    const waitingButton = screen.getByRole("button", {
      name: /Copiar lista de espera/i,
    });
    await fireEvent.click(waitingButton);

    // Verify clipboard.writeText was called
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith("Charlie\nDiana");

    // Verify button text changes to "Copiado"
    expect(screen.getByText("Copiado")).toBeTruthy();

    // Verify button has success variant when copied
    expect(waitingButton.classList.contains("btn-success")).toBe(true);

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Copiar lista de espera/i }),
      ).toBeTruthy();
    });
  });

  it("calls onOpenGameDraft with mapped DraftResponse when Edit button is clicked", async () => {
    const mockonOpenGameDraft = vi.fn();

    render(GameDetail, {
      props: {
        id: 1,
        onOpenGameDraft: mockonOpenGameDraft,
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Verify badge structure before editing
    const nuevoTag = screen.getByText("Nuevo");
    const antiguoTag = screen.getByText("Antiguo");

    expect(nuevoTag.closest(".badge")).toBeInTheDocument();
    expect(nuevoTag.closest(".badge")).toHaveClass("warning");
    expect(antiguoTag.closest(".badge")).toBeInTheDocument();
    expect(antiguoTag.closest(".badge")).toHaveClass("success");

    // Find and click Edit button
    const editButton = screen.getByRole("button", { name: /Editar Jornada/i });
    await fireEvent.click(editButton);

    // Verify onOpenGameDraft was called with correct parameters
    expect(mockonOpenGameDraft).toHaveBeenCalledWith(
      10, // input_snapshot_id
      expect.objectContaining({
        mesas: expect.arrayContaining([
          expect.objectContaining({
            numero: 1,
            jugadores: expect.arrayContaining([
              expect.objectContaining({
                nombre: "Alice",
                is_new: true,
                country: { name: "England", reason: "Algorithm says so" },
              }),
              expect.objectContaining({
                nombre: "Bob",
                is_new: false,
                country: { name: "France", reason: "" },
              }),
            ]),
          }),
        ]),
        tickets_sobrantes: expect.any(Array),
        intentos_usados: expect.any(Number),
      }),
      1, // gameId
    );
  });

  it("verifies badge structure for all is_new tags", async () => {
    render(GameDetail, {
      props: {
        id: 1,
        onOpenGameDraft: vi.fn(),
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Check that all is_new tags are rendered as Badge components
    const nuevoTags = screen.getAllByText("Nuevo");
    const antiguoTags = screen.getAllByText("Antiguo");

    // Verify Nuevo badges have warning variant
    nuevoTags.forEach((tag) => {
      const badge = tag.closest(".badge");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("warning");
      expect(badge).toHaveClass("fixed-width");
    });

    // Verify Antiguo badges have success variant
    antiguoTags.forEach((tag) => {
      const badge = tag.closest(".badge");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("success");
      expect(badge).toHaveClass("fixed-width");
    });
  });

  describe("country.reason clipboard integration", () => {
    it("includes footnote marker in clipboard copy for player with country.reason", async () => {
      render(GameDetail, {
        props: {
          id: 1,
          onOpenGameDraft: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Click the copy players button
      const playersButton = screen.getByRole("button", {
        name: /Copiar jugadores/i,
      });
      await fireEvent.click(playersButton);

      // Verify the clipboard includes footnote marker (asterisk) for Alice
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining("Alice (Inglaterra*)"),
      );

      // Verify Bob has no asterisk (no country.reason)
      const clipboardText = mockClipboard.writeText.mock
        .calls[0]?.[0] as string;
      expect(clipboardText).toContain("Bob (Francia)");
      expect(clipboardText).not.toContain("Bob (Francia*)");

      // Verify the clipboard includes the footnote explanation
      expect(clipboardText).toContain("* Algorithm says so");
    });
  });

  describe("country_reason DOM rendering", () => {
    it("renders info icon and tooltip only for players with country_reason", async () => {
      render(GameDetail, {
        props: {
          id: 1,
          onOpenGameDraft: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Find all info icons (should only be for Alice who has country.reason)
      const infoIcons = document.querySelectorAll(".info-icon");
      expect(infoIcons.length).toBe(1);

      // Find all tooltips (should only be for Alice)
      const tooltips = document.querySelectorAll(
        ".tooltip-cell .tooltip-trigger",
      );
      expect(tooltips.length).toBe(1);

      // Verify the tooltip trigger exists and has the info icon
      const tooltipTrigger = tooltips[0];
      expect(tooltipTrigger).toBeDefined();
      if (tooltipTrigger) {
        expect(tooltipTrigger).toBeInTheDocument();
        expect(tooltipTrigger.querySelector(".info-icon")).toBeInTheDocument();
      }
    });
  });

  describe("country_reason DOM rendering", () => {
    it("renders info icon and tooltip only for players with country_reason", async () => {
      render(GameDetail, {
        props: {
          id: 1,
          onOpenGameDraft: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Find all info icons (should only be for Alice who has country.reason)
      const infoIcons = document.querySelectorAll(".info-icon");
      expect(infoIcons.length).toBe(1);

      // Find all tooltips (should only be for Alice)
      const tooltips = document.querySelectorAll(
        ".tooltip-cell .tooltip-trigger",
      );
      expect(tooltips.length).toBe(1);

      // Verify the tooltip trigger exists and has the info icon
      const tooltipTrigger = tooltips[0];
      expect(tooltipTrigger).toBeDefined();

      // Click the copy players button
      const playersButton = screen.getByRole("button", {
        name: /Copiar jugadores/i,
      });
      await fireEvent.click(playersButton);

      // Verify the clipboard includes footnote marker (asterisk) for Alice
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining("Alice (Inglaterra*)"),
      );

      // Verify Bob has no asterisk (no country.reason)
      const clipboardText = mockClipboard.writeText.mock
        .calls[0]?.[0] as string;
      expect(clipboardText).toContain("Bob (Francia)");
      expect(clipboardText).not.toContain("Bob (Francia*)");

      // Verify the clipboard includes the footnote explanation
      expect(clipboardText).toContain("* Algorithm says so");
    });
  });

  describe("country_reason DOM rendering", () => {
    it("renders info icon and tooltip only for players with country_reason", async () => {
      render(GameDetail, {
        props: {
          id: 1,
          onOpenGameDraft: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Find all info icons (should only be for Alice who has country.reason)
      const infoIcons = document.querySelectorAll(".info-icon");
      expect(infoIcons.length).toBe(1);

      // Find all tooltips (should only be for Alice)
      const tooltips = document.querySelectorAll(
        ".tooltip-cell .tooltip-trigger",
      );
      expect(tooltips.length).toBe(1);

      // Verify the tooltip trigger exists and has the info icon
      const tooltipTrigger = tooltips[0];
      expect(tooltipTrigger).toBeDefined();
      if (tooltipTrigger) {
        expect(tooltipTrigger).toBeInTheDocument();
        expect(tooltipTrigger.querySelector(".info-icon")).toBeInTheDocument();
      }

      // Trigger hover to render portal popover
      if (tooltipTrigger) {
        await fireEvent.mouseEnter(tooltipTrigger);
      }
      await tick();

      // Verify tooltip contains reason text in document body
      const tooltipPopover = document.body.querySelector(".tooltip-popover");
      expect(tooltipPopover).toHaveTextContent("Algorithm says so");
    });

    it("renders no info icons when no players have country.reason", async () => {
      // Override the mock for this specific test
      apiGameSpy.mockResolvedValueOnce(
        mockApiSuccess({
          ...defaultGameData,
          mesas: [
            {
              numero: 1,
              gm: createMockDraftPlayer({ nombre: "GameMaster1" }),
              jugadores: [
                createMockDraftPlayer({
                  nombre: "Alice",
                  is_new: true,
                  country: { name: "England", reason: "" },
                }),
                createMockDraftPlayer({
                  nombre: "Bob",
                  is_new: false,
                  country: { name: "France", reason: "" },
                }),
              ],
            },
          ],
        } as GameDetailResponse),
      );

      render(GameDetail, {
        props: { id: 1, onOpenGameDraft: vi.fn() },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Verify no info icons or tooltips are rendered
      const infoIcons = document.querySelectorAll(".info-icon");
      expect(infoIcons.length).toBe(0);

      const reasonTooltips = document.querySelectorAll(".reason-tooltip");
      expect(reasonTooltips.length).toBe(0);
    });
  });
});
