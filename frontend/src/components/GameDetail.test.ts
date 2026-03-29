import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import GameDetail from "./GameDetail.svelte";

// Mock the API module
vi.mock("../api", () => ({
  fetchGame: vi.fn().mockResolvedValue({
    id: 1,
    created_at: "2024-01-01T00:00:00Z",
    intentos: 3,
    copypaste: "Player1\nPlayer2\nPlayer3",
    input_snapshot_id: 10,
    output_snapshot_id: 20,
    mesas: [
      {
        numero: 1,
        gm: "GameMaster1",
        jugadores: [
          { nombre: "Alice", etiqueta: "Nuevo", pais: "England" },
          { nombre: "Bob", etiqueta: "Antiguo", pais: "France" },
        ],
      },
    ],
    waiting_list: [
      { nombre: "Charlie", cupos: "2 cupos" },
      { nombre: "Diana", cupos: "1 cupo" },
    ],
  }),
}));

// Mock the utils module
vi.mock("../utils", () => ({
  esc: vi.fn((s: string | null | undefined) => s ?? ""),
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
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders game details with mesas and waiting list", async () => {
    render(GameDetail, {
      props: {
        id: 1,
        openGameDraft: vi.fn(),
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Verify game info is displayed
    expect(screen.getByText(/Resumen/)).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy(); // intentos

    // Verify mesas are displayed
    expect(screen.getByText("Partida 1")).toBeTruthy();
    expect(screen.getByText("GM: GameMaster1")).toBeTruthy();
    expect(screen.getByText("Alice 🇬🇧")).toBeTruthy();
    expect(screen.getByText("Bob 🇫🇷")).toBeTruthy();

    // Verify waiting list is displayed
    expect(screen.getByText("Lista de espera")).toBeTruthy();
    expect(screen.getByText("Charlie")).toBeTruthy();
    expect(screen.getByText("Diana")).toBeTruthy();

    // Verify that experience tags are wrapped in tag-wrapper divs
    const nuevoTag = screen.getByText("Nuevo");
    const antiguoTag = screen.getByText("Antiguo");

    expect(nuevoTag.closest(".tag-wrapper")).toBeInTheDocument();
    expect(antiguoTag.closest(".tag-wrapper")).toBeInTheDocument();
  });

  it("copies share list and shows feedback when share button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
        openGameDraft: vi.fn(),
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
    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      "Player1\nPlayer2\nPlayer3",
    );

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
        openGameDraft: vi.fn(),
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

    // Verify clipboard.writeText was called
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      "Alice (England)\nBob (France)",
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
        openGameDraft: vi.fn(),
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

  it("calls openGameDraft with mapped DraftResponse when Edit button is clicked", async () => {
    const mockOpenGameDraft = vi.fn();

    render(GameDetail, {
      props: {
        id: 1,
        openGameDraft: mockOpenGameDraft,
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Verify tag-wrapper structure before editing
    const nuevoTag = screen.getByText("Nuevo");
    const antiguoTag = screen.getByText("Antiguo");

    expect(nuevoTag.closest(".tag-wrapper")).toBeInTheDocument();
    expect(antiguoTag.closest(".tag-wrapper")).toBeInTheDocument();

    // Find and click Edit button
    const editButton = screen.getByRole("button", { name: /Editar Jornada/i });
    await fireEvent.click(editButton);

    // Verify openGameDraft was called with correct parameters
    expect(mockOpenGameDraft).toHaveBeenCalledWith(
      10, // input_snapshot_id
      expect.objectContaining({
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        mesas: expect.arrayContaining([
          expect.objectContaining({
            numero: 1,
            // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
            jugadores: expect.arrayContaining([
              expect.objectContaining({
                nombre: "Alice",
                pais: "England",
              }),
              expect.objectContaining({
                nombre: "Bob",
                pais: "France",
              }),
            ]),
          }),
        ]),
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        tickets_sobrantes: expect.any(Array),
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        intentos_usados: expect.any(Number),
      }),
      1, // gameId
    );
  });

  it("verifies tag-wrapper structure for all experience tags", async () => {
    render(GameDetail, {
      props: {
        id: 1,
        openGameDraft: vi.fn(),
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Check that all experience tags are wrapped in tag-wrapper divs
    const allTags = screen.getAllByText(/Nuevo|Antiguo/);

    allTags.forEach((tag) => {
      const wrapper = tag.closest(".tag-wrapper");
      expect(wrapper).toBeInTheDocument();
      expect(wrapper?.tagName).toBe("DIV");
    });
  });
});
