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

// Mock window.alert
vi.stubGlobal("alert", vi.fn());

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
});
