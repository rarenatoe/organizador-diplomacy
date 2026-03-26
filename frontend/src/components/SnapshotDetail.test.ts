import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import SnapshotDetail from "./SnapshotDetail.svelte";

// Mock the API module
vi.mock("../api", () => ({
  fetchSnapshot: vi.fn().mockResolvedValue({
    id: 1,
    created_at: "2024-01-01T00:00:00Z",
    source: "manual",
    players: [
      {
        nombre: "Alice",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "Bob",
        experiencia: "Antiguo",
        juegos_este_ano: 3,
        prioridad: 1,
        partidas_deseadas: 2,
        partidas_gm: 1,
      },
    ],
  }),
  runScript: vi.fn().mockResolvedValue({ returncode: 0 }),
  renamePlayer: vi.fn().mockResolvedValue({}),
  fetchChain: vi.fn().mockResolvedValue({ roots: [] }),
  fetchNotionPlayers: vi.fn().mockResolvedValue({ players: [] }),
  saveSnapshot: vi.fn().mockResolvedValue({ snapshot_id: 2 }),
}));

// Mock the stores
vi.mock("../stores.svelte", () => ({
  setActiveNodeId: vi.fn(),
}));

// Mock the syncUtils
vi.mock("../syncUtils", () => ({
  detectSimilarNames: vi.fn().mockReturnValue([]),
}));

// Mock the snapshotUtils
vi.mock("../snapshotUtils", () => ({
  findLatestGameId: vi.fn().mockReturnValue(null),
}));

// Mock navigator.clipboard
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.defineProperty(navigator, "clipboard", {
  value: mockClipboard,
  writable: true,
});

describe("SnapshotDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders snapshot details with players", async () => {
    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft: () => {},
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Verify snapshot info is displayed
    expect(screen.getByText(/Snapshot #1/)).toBeTruthy();
    expect(screen.getByText(/📥 Manual/)).toBeTruthy();

    // Verify players are displayed
    expect(screen.getByText("Alice")).toBeTruthy();
    expect(screen.getByText("Bob")).toBeTruthy();
  });

  it("passes current players to onEditDraft when edit button is clicked", async () => {
    const onEditDraft = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft,
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click the edit button
    const editButton = screen.getByText("📝 Editar");
    await fireEvent.click(editButton);

    // Verify onEditDraft was called with correct parameters
    expect(onEditDraft).toHaveBeenCalledTimes(1);
    expect(onEditDraft).toHaveBeenCalledWith(1, "manual", null, [
      {
        nombre: "Alice",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "Bob",
        experiencia: "Antiguo",
        juegos_este_ano: 3,
        prioridad: 1,
        partidas_deseadas: 2,
        partidas_gm: 1,
      },
    ]);
  });

  it("passes empty array when snapshot has no players", async () => {
    const { fetchSnapshot } = await import("../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: 2,
      created_at: "2024-01-01T00:00:00Z",
      source: "manual",
      players: [],
    });

    const onEditDraft = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 2,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft,
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click the edit button
    const editButton = screen.getByText("📝 Editar");
    await fireEvent.click(editButton);

    // Verify onEditDraft was called with empty array
    expect(onEditDraft).toHaveBeenCalledTimes(1);
    expect(onEditDraft).toHaveBeenCalledWith(2, "manual", null, []);
  });

  it("handles players with missing fields gracefully", async () => {
    const { fetchSnapshot } = await import("../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: 3,
      created_at: "2024-01-01T00:00:00Z",
      source: "manual",
      players: [
        {
          nombre: "Charlie",
          // Missing other fields
        },
      ],
    });

    const onEditDraft = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 3,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft,
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click the edit button
    const editButton = screen.getByText("📝 Editar");
    await fireEvent.click(editButton);

    // Verify onEditDraft was called with default values for missing fields
    expect(onEditDraft).toHaveBeenCalledTimes(1);
    expect(onEditDraft).toHaveBeenCalledWith(3, "manual", null, [
      {
        nombre: "Charlie",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
    ]);
  });

  it("copies CSV to clipboard when copy button is clicked", async () => {
    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft: () => {},
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click the copy button
    const copyButton = screen.getByText("📋 Copiar tabla CSV");
    await fireEvent.click(copyButton);

    // Verify clipboard.writeText was called
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining(
        "nombre,experiencia,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm",
      ),
    );
  });

  it("shows copy feedback when CSV copy button is clicked", async () => {
    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft: () => {},
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Find the copy button
    const copyButton = screen.getByText("📋 Copiar tabla CSV");
    await fireEvent.click(copyButton);

    // Verify button text changes to "✅ Copiado"
    expect(screen.getByText("✅ Copiado")).toBeTruthy();

    // Verify button has 'ok' class
    expect(copyButton.classList.contains("ok")).toBe(true);

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(screen.getByText("📋 Copiar tabla CSV")).toBeTruthy();
    });
  });

  it("calls onChainUpdate after successful organizar", async () => {
    // Use real timers for this test to avoid async issues
    vi.useRealTimers();

    const api = await import("../api");
    const onChainUpdateMock = vi.fn(() => {});
    const onOpenGameMock = vi.fn(() => {});

    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => onChainUpdateMock(),
        onOpenSnapshot: () => {},
        onOpenGame: () => onOpenGameMock(),
        onEditDraft: () => {},
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click the organizar button
    const organizarButton = screen.getByText("▶ Organizar Partidas");
    await fireEvent.click(organizarButton);

    // Verify runScript was called
    await waitFor(() => {
      expect(api.runScript).toHaveBeenCalledWith("organizar", 1);
    });

    // Verify onChainUpdate was called
    await waitFor(() => {
      expect(onChainUpdateMock).toHaveBeenCalledTimes(1);
    });

    // Restore fake timers for other tests
    vi.useFakeTimers();
  });

  it("calls onShowError and stops when organizar returns non-zero", async () => {
    vi.useRealTimers();

    const api = await import("../api");
    (api.runScript as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      returncode: 1,
      stdout: "No hay suficientes jugadores",
      stderr: "",
    });

    const onChainUpdateMock = vi.fn();
    const onOpenGameMock = vi.fn();
    const onShowErrorMock = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: onChainUpdateMock,
        onOpenSnapshot: () => {},
        onOpenGame: onOpenGameMock,
        onEditDraft: () => {},
        onShowError: onShowErrorMock,
      },
    });

    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

    await waitFor(() => {
      expect(onShowErrorMock).toHaveBeenCalledWith(
        "Error al organizar",
        "No hay suficientes jugadores",
      );
    });
    expect(onChainUpdateMock).not.toHaveBeenCalled();
    expect(onOpenGameMock).not.toHaveBeenCalled();

    vi.useFakeTimers();
  });

  it('calls onShowError and stops when organizar stdout includes "No hay suficientes"', async () => {
    vi.useRealTimers();

    const api = await import("../api");
    (api.runScript as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      returncode: 0,
      stdout: "No hay suficientes mesas para organizar",
      stderr: "",
    });

    const onChainUpdateMock = vi.fn();
    const onOpenGameMock = vi.fn();
    const onShowErrorMock = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: onChainUpdateMock,
        onOpenSnapshot: () => {},
        onOpenGame: onOpenGameMock,
        onEditDraft: () => {},
        onShowError: onShowErrorMock,
      },
    });

    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

    await waitFor(() => {
      expect(onShowErrorMock).toHaveBeenCalledWith(
        "Error al organizar",
        "No hay suficientes mesas para organizar",
      );
    });
    expect(onChainUpdateMock).not.toHaveBeenCalled();
    expect(onOpenGameMock).not.toHaveBeenCalled();

    vi.useFakeTimers();
  });

  it("should prevent Sincronizar Notion if snapshot source is already notion_sync", async () => {
    const { fetchSnapshot, fetchNotionPlayers } = await import("../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: 4,
      source: "notion_sync",
      created_at: "2024-01-01 12:00:00",
      players: [
        {
          nombre: "Alice",
          experiencia: "Nuevo",
          juegos_este_ano: 0,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
        },
      ],
    });

    const onShowError = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 4,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft: () => {},
        onShowError,
      },
    });

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click "Sincronizar Notion"
    const syncBtn = screen.getByText(/Sincronizar Notion/);
    await fireEvent.click(syncBtn);

    // Assert fail-fast behavior: onShowError called, fetchNotionPlayers NOT called
    expect(onShowError).toHaveBeenCalledWith(
      "Acción no permitida",
      "El snapshot base ya fue generado por notion_sync y aún no se ha jugado una partida.",
    );
    expect(fetchNotionPlayers).not.toHaveBeenCalled();
  });

  it("should allow Sincronizar Notion if snapshot source is manual", async () => {
    const { fetchSnapshot, fetchNotionPlayers } = await import("../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: 5,
      source: "manual",
      created_at: "2024-01-01 12:00:00",
      players: [],
    });

    (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      players: [],
      error: undefined,
    });

    render(SnapshotDetail, {
      props: {
        id: 5,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onEditDraft: () => {},
        onShowError: () => {},
      },
    });

    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click "Sincronizar Notion"
    const syncBtn = screen.getByText(/Sincronizar Notion/);
    await fireEvent.click(syncBtn);

    // Assert it proceeds to fetch Notion players
    await waitFor(() => {
      expect(fetchNotionPlayers).toHaveBeenCalled();
    });
  });
});
