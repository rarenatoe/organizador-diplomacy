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
        nombre: "P1",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P2",
        experiencia: "Antiguo",
        juegos_este_ano: 3,
        prioridad: 1,
        partidas_deseadas: 2,
        partidas_gm: 1,
      },
      {
        nombre: "P3",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P4",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P5",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P6",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P7",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
    ],
  }),
  runScript: vi.fn().mockResolvedValue({ returncode: 0 }),
  renamePlayer: vi.fn().mockResolvedValue({}),
  fetchChain: vi.fn().mockResolvedValue({ roots: [] }),
  fetchNotionPlayers: vi
    .fn()
    .mockResolvedValue({ players: [], similar_names: [] }),
  saveSnapshot: vi.fn().mockResolvedValue({ snapshot_id: 2 }),
}));

// Mock the stores
vi.mock("../stores.svelte", () => ({
  setActiveNodeId: vi.fn(),
}));

// Mock the syncUtils
vi.mock("../syncUtils", () => ({
  validateOrganizar: vi.fn().mockReturnValue(null),
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
        onOpenGameDraft: () => {},
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
    expect(screen.getByText("P1")).toBeTruthy();
    expect(screen.getByText("P2")).toBeTruthy();
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
        onOpenGameDraft: () => {},
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
        nombre: "P1",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P2",
        experiencia: "Antiguo",
        juegos_este_ano: 3,
        prioridad: 1,
        partidas_deseadas: 2,
        partidas_gm: 1,
      },
      {
        nombre: "P3",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P4",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P5",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P6",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
      },
      {
        nombre: "P7",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
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
        onOpenGameDraft: () => {},
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
        onOpenGameDraft: () => {},
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
        onOpenGameDraft: () => {},
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
        onOpenGameDraft: () => {},
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

  it("calls onOpenGameDraft after successful organizar", async () => {
    // Use real timers for this test to avoid async issues
    vi.useRealTimers();

    const onOpenGameDraft = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onOpenGameDraft,
        onEditDraft: () => {},
        onShowError: () => {},
      },
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    const organizarButton = screen.getByText("▶ Organizar Partidas");
    await fireEvent.click(organizarButton);

    // Verify onOpenGameDraft was called
    expect(onOpenGameDraft).toHaveBeenCalledWith(1);
  });

  it("calls onOpenGameDraft and stops when organizar returns non-zero", async () => {
    vi.useRealTimers();

    const api = await import("../api");
    (api.runScript as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      returncode: 1,
      stdout: "No hay suficientes jugadores",
      stderr: "",
    });

    const onOpenGameDraft = vi.fn();
    const onShowErrorMock = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onOpenGameDraft,
        onEditDraft: () => {},
        onShowError: onShowErrorMock,
      },
    });

    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

    // Should call onOpenGameDraft regardless of validation
    expect(onOpenGameDraft).toHaveBeenCalledWith(1);
  });

  it("calls onOpenGameDraft when organizar stdout includes 'No hay suficientes'", async () => {
    vi.useRealTimers();

    const api = await import("../api");
    (api.runScript as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      returncode: 0,
      stdout: "No hay suficientes mesas para organizar",
      stderr: "",
    });

    const onOpenGameDraft = vi.fn();
    const onShowErrorMock = vi.fn();

    render(SnapshotDetail, {
      props: {
        id: 1,
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onOpenGame: () => {},
        onOpenGameDraft,
        onEditDraft: () => {},
        onShowError: onShowErrorMock,
      },
    });

    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

    // Should call onOpenGameDraft regardless
    expect(onOpenGameDraft).toHaveBeenCalledWith(1);
  });

  it("should prevent Sincronizar Notion if snapshot source is already notion_sync", async () => {
    const { fetchSnapshot, fetchNotionPlayers } = await import("../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: 4,
      source: "notion_sync",
      created_at: "2024-01-01 12:00:00",
      players: [
        {
          nombre: "P1",
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
        onOpenGameDraft: () => {},
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
        onOpenGameDraft: () => {},
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

  describe("Organizar Validation", () => {
    it("should hard block if less than 7 players", async () => {
      const { fetchSnapshot } = await import("../api");
      const onOpenGameDraft = vi.fn();
      const onShowError = vi.fn();

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        id: 10,
        players: new Array(6)
          .fill(null)
          .map((_, i) => ({ nombre: `P${i}`, partidas_deseadas: 1 })),
      });

      render(SnapshotDetail, {
        props: {
          id: 10,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft,
          onEditDraft: () => {},
          onShowError,
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

      expect(onShowError).toHaveBeenCalledWith(
        "Error al organizar",
        "Se necesitan al menos 7 jugadores para organizar partidas.",
      );
      expect(onOpenGameDraft).not.toHaveBeenCalled();
    });

    it("should show modal if all players have 1 ticket", async () => {
      const { fetchSnapshot } = await import("../api");
      const { validateOrganizar } = await import("../syncUtils");
      const onOpenGameDraft = vi.fn();

      const players = new Array(7).fill(null).map((_, i) => ({
        nombre: `P${i}`,
        partidas_deseadas: 1,
        partidas_gm: 0,
        prioridad: 0,
      }));

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        id: 11,
        players,
      });
      (validateOrganizar as ReturnType<typeof vi.fn>).mockReturnValueOnce({
        isAllOnes: true,
        gmShortage: { required: 1, assigned: 0 },
        excludedPlayers: [],
      });

      render(SnapshotDetail, {
        props: {
          id: 11,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft,
          onEditDraft: () => {},
          onShowError: () => {},
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

      expect(screen.getByText("Revisar Roster")).toBeTruthy();
      expect(onOpenGameDraft).not.toHaveBeenCalled();
    });

    it("should call executeOrganizar when confirmed in modal", async () => {
      vi.useRealTimers();
      const { fetchSnapshot } = await import("../api");
      const { validateOrganizar } = await import("../syncUtils");
      const onOpenGameDraft = vi.fn();

      const players = new Array(7).fill(null).map((_, i) => ({
        nombre: `P${i}`,
        partidas_deseadas: 1,
        partidas_gm: 0,
        prioridad: 0,
      }));

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        id: 12,
        players,
      });
      (validateOrganizar as ReturnType<typeof vi.fn>).mockReturnValueOnce({
        isAllOnes: true,
        gmShortage: null,
        excludedPlayers: [],
      });

      render(SnapshotDetail, {
        props: {
          id: 12,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft,
          onEditDraft: () => {},
          onShowError: () => {},
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

      const confirmBtn = screen.getByText("Organizar de todos modos");
      await fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(onOpenGameDraft).toHaveBeenCalledWith(12);
      });
      vi.useFakeTimers();
    });

    it("should call onEditDraft when edit is clicked in modal", async () => {
      const { fetchSnapshot } = await import("../api");
      const { validateOrganizar } = await import("../syncUtils");

      const players = new Array(7).fill(null).map((_, i) => ({
        nombre: `P${i}`,
        partidas_deseadas: 1,
        partidas_gm: 0,
        prioridad: 0,
        experiencia: "Nuevo",
        juegos_este_ano: 0,
      }));

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        id: 13,
        players,
      });
      (validateOrganizar as ReturnType<typeof vi.fn>).mockReturnValueOnce({
        isAllOnes: true,
        gmShortage: null,
        excludedPlayers: [],
      });

      const onEditDraft = vi.fn();
      render(SnapshotDetail, {
        props: {
          id: 13,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft: () => {},
          onEditDraft,
          onShowError: () => {},
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(screen.getByText("▶ Organizar Partidas"));

      const editBtn = screen.getByText("Volver a Editar");
      await fireEvent.click(editBtn);

      expect(onEditDraft).toHaveBeenCalledTimes(1);
      expect(onEditDraft).toHaveBeenCalledWith(
        13,
        "manual",
        null,
        expect.arrayContaining([expect.objectContaining({ nombre: "P0" })]),
      );
    });
  });
});
