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
          { nombre: "Alice", etiqueta: "Nuevo" },
          { nombre: "Bob", etiqueta: "Antiguo" },
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
    expect(screen.getByText("Alice")).toBeTruthy();
    expect(screen.getByText("Bob")).toBeTruthy();

    // Verify waiting list is displayed
    expect(screen.getByText("Lista de espera")).toBeTruthy();
    expect(screen.getByText("Charlie")).toBeTruthy();
    expect(screen.getByText("Diana")).toBeTruthy();
  });

  it("copies share list and shows feedback when share button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Find the share copy button
    const shareButton = screen.getByText("📋 Copiar lista para compartir");
    await fireEvent.click(shareButton);

    // Verify clipboard.writeText was called
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      "Player1\nPlayer2\nPlayer3",
    );

    // Verify button text changes to "✅ Copiado"
    expect(screen.getByText("✅ Copiado")).toBeTruthy();

    // Verify button has 'ok' class
    expect(shareButton.classList.contains("ok")).toBe(true);

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(screen.getByText("📋 Copiar lista para compartir")).toBeTruthy();
    });
  });

  it("copies players list and shows feedback when players button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Find the players copy button
    const playersButton = screen.getByText("📋 Copiar jugadores");
    await fireEvent.click(playersButton);

    // Verify clipboard.writeText was called
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith("Alice\nBob");

    // Verify button text changes to "✅ Copiado"
    expect(screen.getByText("✅ Copiado")).toBeTruthy();

    // Verify button has 'ok' class
    expect(playersButton.classList.contains("ok")).toBe(true);

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(screen.getByText("📋 Copiar jugadores")).toBeTruthy();
    });
  });

  it("copies waiting list and shows feedback when waiting button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Find the waiting list copy button
    const waitingButton = screen.getByText("📋 Copiar lista de espera");
    await fireEvent.click(waitingButton);

    // Verify clipboard.writeText was called
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith("Charlie\nDiana");

    // Verify button text changes to "✅ Copiado"
    expect(screen.getByText("✅ Copiado")).toBeTruthy();

    // Verify button has 'ok' class
    expect(waitingButton.classList.contains("ok")).toBe(true);

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(screen.getByText("📋 Copiar lista de espera")).toBeTruthy();
    });
  });

  it("resets feedback when another button is clicked", async () => {
    render(GameDetail, {
      props: {
        id: 1,
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click share button
    const shareButton = screen.getByText("📋 Copiar lista para compartir");
    await fireEvent.click(shareButton);

    // Verify share button shows feedback
    expect(screen.getByText("✅ Copiado")).toBeTruthy();

    // Click waiting button before timeout
    const waitingButton = screen.getByText("📋 Copiar lista de espera");
    await fireEvent.click(waitingButton);

    // Verify waiting button shows feedback
    expect(screen.getByText("✅ Copiado")).toBeTruthy();

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify waiting button reverts
    await waitFor(() => {
      expect(screen.getByText("📋 Copiar lista de espera")).toBeTruthy();
    });
  });
});
