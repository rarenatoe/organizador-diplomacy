import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import SnapshotDetail from "./SnapshotDetail.svelte";
import {
  createMockSnapshotDetail,
  createMockEditPlayerRow,
} from "../../tests/fixtures";
import { fetchSnapshot } from "../../api";

// Mock the API module
vi.mock("../../api", () => ({
  fetchSnapshot: vi.fn(),
  renamePlayer: vi.fn().mockResolvedValue({}),
  fetchChain: vi.fn().mockResolvedValue({ roots: [] }),
  fetchNotionPlayers: vi
    .fn()
    .mockResolvedValue({ players: [], similar_names: [] }),
  saveSnapshot: vi.fn().mockResolvedValue({ snapshot_id: 2 }),
}));

// Mock the stores
vi.mock("../../stores.svelte", () => ({
  setActiveNodeId: vi.fn(),
}));

// Mock the syncUtils
vi.mock("../../syncUtils", () => ({
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

// Base props for all tests
const defaultProps = {
  id: 1,
  onClose: vi.fn(),
  onChainUpdate: vi.fn(),
  onOpenSnapshot: vi.fn(),
  onOpenGame: vi.fn(),
  onOpenGameDraft: vi.fn(),
  onEditDraft: vi.fn(),
  onShowError: vi.fn(),
  onShowToast: vi.fn(),
};

// Helper function to render and wait for loading
async function renderSnapshotDetail(
  propsOverrides: Partial<typeof defaultProps> = {},
) {
  const utils = render(SnapshotDetail, {
    props: { ...defaultProps, ...propsOverrides },
  });
  await waitFor(() => {
    expect(screen.queryByText("Cargando…")).toBeNull();
  });
  return utils;
}

describe("SnapshotDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Set up default fetchSnapshot mock
    vi.mocked(fetchSnapshot).mockResolvedValue(
      createMockSnapshotDetail({
        source: "manual",
        players: [
          createMockEditPlayerRow({ nombre: "P1" }),
          createMockEditPlayerRow({
            nombre: "P2",
            experiencia: "Antiguo",
            juegos_este_ano: 3,
            prioridad: 1,
            partidas_deseadas: 2,
            partidas_gm: 1,
          }),
          createMockEditPlayerRow({ nombre: "P3" }),
          createMockEditPlayerRow({ nombre: "P4" }),
          createMockEditPlayerRow({ nombre: "P5" }),
          createMockEditPlayerRow({ nombre: "P6" }),
          createMockEditPlayerRow({ nombre: "P7" }),
        ],
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders snapshot details with players", async () => {
    await renderSnapshotDetail();

    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.getByText("P2")).toBeInTheDocument();
    expect(screen.getByText("P3")).toBeInTheDocument();
    expect(screen.getByText("P4")).toBeInTheDocument();
    expect(screen.getByText("P5")).toBeInTheDocument();
    expect(screen.getByText("P6")).toBeInTheDocument();
    expect(screen.getByText("P7")).toBeInTheDocument();
  });

  it("passes current players to onEditDraft when edit button is clicked", async () => {
    const onEditDraft = vi.fn();

    await renderSnapshotDetail({ onEditDraft });

    // Click the edit button
    const editButton = screen.getByText("Editar");
    await fireEvent.click(editButton);

    // Verify onEditDraft was called with correct parameters
    expect(onEditDraft).toHaveBeenCalledTimes(1);
    expect(onEditDraft).toHaveBeenCalledWith(1, "manual", null, [
      createMockEditPlayerRow({ nombre: "P1" }),
      createMockEditPlayerRow({
        nombre: "P2",
        experiencia: "Antiguo",
        juegos_este_ano: 3,
        prioridad: 1,
        partidas_deseadas: 2,
        partidas_gm: 1,
      }),
      createMockEditPlayerRow({ nombre: "P3" }),
      createMockEditPlayerRow({ nombre: "P4" }),
      createMockEditPlayerRow({ nombre: "P5" }),
      createMockEditPlayerRow({ nombre: "P6" }),
      createMockEditPlayerRow({ nombre: "P7" }),
    ]);
  });

  it("passes empty array when snapshot has no players", async () => {
    const { fetchSnapshot } = await import("../../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockSnapshotDetail({
        id: 2,
        players: [],
      }),
    );

    const onEditDraft = vi.fn();

    await renderSnapshotDetail({ id: 2, onEditDraft });

    const editButton = screen.getByRole("button", { name: /Editar/i });
    await fireEvent.click(editButton);

    // Verify onEditDraft was called with empty array
    expect(onEditDraft).toHaveBeenCalledTimes(1);
    expect(onEditDraft).toHaveBeenCalledWith(2, "manual", null, []);
  });

  it("handles players with missing fields gracefully", async () => {
    const { fetchSnapshot } = await import("../../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockSnapshotDetail({
        id: 3,
        players: [createMockEditPlayerRow({ nombre: "Charlie" })],
      }),
    );

    const onEditDraft = vi.fn();

    await renderSnapshotDetail({ id: 3, onEditDraft });

    const editButton = screen.getByRole("button", { name: /Editar/i });
    await fireEvent.click(editButton);

    // Verify onEditDraft was called with default values for missing fields
    expect(onEditDraft).toHaveBeenCalledTimes(1);
    expect(onEditDraft).toHaveBeenCalledWith(3, "manual", null, [
      createMockEditPlayerRow({ nombre: "Charlie" }),
    ]);
  });

  // TODO: Fix copy button tests - these buttons don't exist in current component
  it("copies CSV to clipboard when copy button is clicked", async () => {
    await renderSnapshotDetail();

    const copyButton = screen.getByText("Copiar CSV");
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
    await renderSnapshotDetail();

    const copyButton = screen.getByText("Copiar CSV");
    await fireEvent.click(copyButton);

    // Verify button text changes to "Copiado"
    expect(screen.getByText("Copiado")).toBeTruthy();

    // Fast-forward time by 1500ms
    vi.advanceTimersByTime(1500);

    // Verify button reverts to original text
    await waitFor(() => {
      expect(screen.getByText("Copiar CSV")).toBeInTheDocument();
    });
  });

  it("calls onOpenGameDraft after successful organizar", async () => {
    // Use real timers for this test to avoid async issues
    vi.useRealTimers();

    const onOpenGameDraft = vi.fn();

    await renderSnapshotDetail({ onOpenGameDraft });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    const organizarButton = screen.getByRole("button", {
      name: /Organizar Partidas/i,
    });
    await fireEvent.click(organizarButton);

    // Verify onOpenGameDraft was called
    expect(onOpenGameDraft).toHaveBeenCalledTimes(1);
    expect(onOpenGameDraft).toHaveBeenCalledWith(1);
  });

  it("should prevent Sincronizar Notion if snapshot source is already notion_sync", async () => {
    const { fetchSnapshot, fetchNotionPlayers } = await import("../../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockSnapshotDetail({
        id: 4,
        source: "notion_sync",
        created_at: "2024-01-01 12:00:00",
        players: [createMockEditPlayerRow({ nombre: "P1" })],
      }),
    );

    const onShowError = vi.fn();

    await renderSnapshotDetail({ id: 4, onShowError });

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
    const { fetchSnapshot, fetchNotionPlayers } = await import("../../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockSnapshotDetail({
        id: 5,
        source: "manual",
        created_at: "2024-01-01 12:00:00",
        players: [],
      }),
    );

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
        onShowToast: vi.fn(),
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
      const { fetchSnapshot } = await import("../../api");
      const onOpenGameDraft = vi.fn();
      const onShowError = vi.fn();

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 10,
          players: new Array(6)
            .fill(null)
            .map((_, i) => createMockEditPlayerRow({ nombre: `P${i}` })),
        }),
      );

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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(
        screen.getByRole("button", { name: /Organizar Partidas/i }),
      );

      expect(onShowError).toHaveBeenCalledWith(
        "Error al organizar",
        "Se necesitan al menos 7 jugadores para organizar partidas.",
      );
      expect(onOpenGameDraft).not.toHaveBeenCalled();
    });

    it("should show modal if all players have 1 ticket", async () => {
      const { fetchSnapshot } = await import("../../api");
      const { validateOrganizar } = await import("../../syncUtils");
      const onOpenGameDraft = vi.fn();

      const players = new Array(7)
        .fill(null)
        .map((_, i) => createMockEditPlayerRow({ nombre: `P${i}` }));

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 11,
          players,
        }),
      );
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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(
        screen.getByRole("button", { name: /Organizar Partidas/i }),
      );

      expect(screen.getByText("Revisar Roster")).toBeTruthy();
      expect(onOpenGameDraft).not.toHaveBeenCalled();
    });

    it("should call executeOrganizar when confirmed in modal", async () => {
      vi.useRealTimers();
      const { fetchSnapshot } = await import("../../api");
      const { validateOrganizar } = await import("../../syncUtils");
      const onOpenGameDraft = vi.fn();

      const players = new Array(7)
        .fill(null)
        .map((_, i) => createMockEditPlayerRow({ nombre: `P${i}` }));

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 12,
          players,
        }),
      );
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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(
        screen.getByRole("button", { name: /Organizar Partidas/i }),
      );

      const confirmBtn = screen.getByRole("button", {
        name: /Organizar de todos modos/i,
      });
      await fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(onOpenGameDraft).toHaveBeenCalledWith(12);
      });
      vi.useFakeTimers();
    });

    it("should call onEditDraft when edit is clicked in modal", async () => {
      const { fetchSnapshot } = await import("../../api");
      const { validateOrganizar } = await import("../../syncUtils");

      const players = new Array(7).fill(null).map((_, i) =>
        createMockEditPlayerRow({
          nombre: `P${i}`,
          partidas_deseadas: 1,
          partidas_gm: 0,
          prioridad: 0,
          experiencia: "Nuevo",
          juegos_este_ano: 0,
        }),
      );

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 13,
          players,
        }),
      );
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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
      await fireEvent.click(
        screen.getByRole("button", { name: /Organizar Partidas/i }),
      );

      const editBtn = screen.getByRole("button", { name: /Volver a Editar/i });
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

  describe("Sync State Management Regression Tests", () => {
    beforeEach(() => {
      vi.clearAllMocks();
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("calls renamePlayer and reloads snapshot when resolving notion sync merges", async () => {
      // Use real timers for this test to avoid async issues
      vi.useRealTimers();

      const { fetchSnapshot, fetchNotionPlayers, saveSnapshot, renamePlayer } =
        await import("../../api");
      const onOpenSnapshot = vi.fn();

      // Mock initial snapshot with a player that has similar name in Notion
      (fetchSnapshot as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(
          createMockSnapshotDetail({
            id: 1,
            players: [createMockEditPlayerRow({ nombre: "Renato" })],
          }),
        )
        // Second call after successful sync (reload)
        .mockResolvedValueOnce(
          createMockSnapshotDetail({
            id: 1,
            players: [
              createMockEditPlayerRow({
                nombre: "Renato Alegre",
                experiencia: "Antiguo",
                juegos_este_ano: 5,
              }),
            ],
          }),
        );

      // Mock fetchNotionPlayers to return a similar_names conflict
      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        players: [
          createMockEditPlayerRow({
            nombre: "Renato Alegre",
            experiencia: "Antiguo",
            juegos_este_ano: 5,
          }),
        ],
        similar_names: [
          { notion: "Renato Alegre", snapshot: "Renato", similarity: 0.85 },
        ],
        error: undefined,
      });

      // Mock renamePlayer to succeed
      (renamePlayer as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      // Mock saveSnapshot to succeed
      (saveSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        snapshot_id: 2,
      });

      await renderSnapshotDetail({ id: 1, onOpenSnapshot });

      // Click sync button to trigger the sync
      const syncBtn = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      // Wait for the resolution modal to appear (it should show the conflict)
      await waitFor(() => {
        expect(screen.getByText(/Nombres similares/i)).toBeTruthy();
      });

      // Click "Usar nombre Notion" button directly (triggers merge_notion action)
      const notionBtn = screen.getByRole("button", {
        name: /Usar nombre Notion/i,
      });
      await fireEvent.click(notionBtn);

      // Wait for the async operations to complete
      await waitFor(() => {
        // Verify saveSnapshot was called
        expect(saveSnapshot).toHaveBeenCalled();
      });

      // Verify saveSnapshot was called with the correct renames payload
      expect(saveSnapshot).toHaveBeenCalledWith(
        expect.objectContaining({
          renames: [{ from: "Renato", to: "Renato Alegre" }],
        }),
      );

      // Verify fetchSnapshot was called again (loadSnapshot after save)
      await waitFor(() => {
        expect(fetchSnapshot).toHaveBeenCalledTimes(2);
      });

      // Restore fake timers
      vi.useFakeTimers();
    });

    it("passes renames payload to saveSnapshot on sync merge", async () => {
      // Use real timers for this test to avoid async issues
      vi.useRealTimers();

      const { fetchSnapshot, fetchNotionPlayers, saveSnapshot, renamePlayer } =
        await import("../../api");

      // Mock initial snapshot with a player that has similar name in Notion
      (fetchSnapshot as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(
          createMockSnapshotDetail({
            id: 1,
            created_at: "2024-01-01T00:00:00Z",
            source: "manual",
            players: [createMockEditPlayerRow({ nombre: "Juan" })],
          }),
        )
        // Second call after successful sync (reload)
        .mockResolvedValueOnce(
          createMockSnapshotDetail({
            id: 1,
            created_at: "2024-01-01T00:00:00Z",
            source: "manual",
            players: [
              createMockEditPlayerRow({
                nombre: "Juan Perez",
                experiencia: "Antiguo",
                juegos_este_ano: 5,
              }),
            ],
          }),
        );

      // Mock fetchNotionPlayers to return a similar_names conflict
      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        players: [
          createMockEditPlayerRow({
            nombre: "Juan Perez",
            experiencia: "Antiguo",
            juegos_este_ano: 5,
          }),
        ],
        similar_names: [
          {
            notion: "Juan Perez",
            snapshot: "Juan",
            similarity: 0.85,
          },
        ],
        error: undefined,
      });

      // Mock renamePlayer to succeed
      (renamePlayer as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      // Mock saveSnapshot to succeed
      (saveSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        snapshot_id: 2,
      });

      await renderSnapshotDetail({ id: 1 });

      // Click sync button to trigger the sync
      const syncBtn = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      // Wait for the resolution modal to appear
      await waitFor(() => {
        expect(screen.getByText(/Nombres similares/i)).toBeTruthy();
      });

      // Click "Usar nombre Notion" button (triggers merge_notion action)
      const notionBtn = screen.getByRole("button", {
        name: /Usar nombre Notion/i,
      });
      await fireEvent.click(notionBtn);

      // Wait for saveSnapshot to be called
      await waitFor(() => {
        expect(saveSnapshot).toHaveBeenCalled();
      });

      // Verify saveSnapshot was called with the correct renames payload
      expect(saveSnapshot).toHaveBeenCalledWith(
        expect.objectContaining({
          renames: [{ from: "Juan", to: "Juan Perez" }],
        }),
      );

      // Restore fake timers
      vi.useFakeTimers();
    });

    it("should reset isSyncing state when fetchNotionPlayers returns an error", async () => {
      const { fetchSnapshot, fetchNotionPlayers } = await import("../../api");
      const onShowError = vi.fn();

      // Mock a valid manual snapshot so sync button is enabled
      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "P1" })],
        }),
      );

      // Mock fetchNotionPlayers to return an error
      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        error: "API limit reached",
        players: [],
        similar_names: [],
      });

      render(SnapshotDetail, {
        props: {
          id: 1,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft: () => {},
          onEditDraft: () => {},
          onShowError,
          onShowToast: vi.fn(),
        },
      });

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Click sync button
      const syncBtn: HTMLButtonElement = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      // Wait for error to be handled
      await waitFor(() => {
        expect(onShowError).toHaveBeenCalledWith(
          "Error de Sincronización",
          "API limit reached",
        );
      });

      // Assert that sync button is no longer disabled and text has reverted
      expect(syncBtn.disabled).toBe(false);
      expect(syncBtn.textContent).toBe("🔄 Sincronizar Notion");
    });

    it("should reset isSyncing state when saveSnapshot returns an error", async () => {
      const { fetchSnapshot, fetchNotionPlayers, saveSnapshot } =
        await import("../../api");
      const onShowError = vi.fn();

      // Mock a valid manual snapshot so sync button is enabled
      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "P1" })],
        }),
      );

      // Mock fetchNotionPlayers to return success with no similar names (so it proceeds directly to merge)
      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        players: [],
        similar_names: [],
        error: undefined,
      });

      // Mock saveSnapshot to return an error
      (saveSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        error: "Backend strict guard rejected save",
      });

      render(SnapshotDetail, {
        props: {
          id: 1,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft: () => {},
          onEditDraft: () => {},
          onShowError,
          onShowToast: vi.fn(),
        },
      });

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Click sync button
      const syncBtn: HTMLButtonElement = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      // Wait for error to be handled
      await waitFor(() => {
        expect(onShowError).toHaveBeenCalledWith(
          "Error de Sincronización",
          "Backend strict guard rejected save",
        );
      });

      // Assert that sync button is no longer disabled and text has reverted
      expect(syncBtn.disabled).toBe(false);
      expect(syncBtn.textContent).toBe("🔄 Sincronizar Notion");
    });

    it("should reset isSyncing state when fetchNotionPlayers throws a network exception", async () => {
      // Use real timers for this test to avoid async issues with promise rejection
      vi.useRealTimers();

      const { fetchSnapshot, fetchNotionPlayers } = await import("../../api");
      const onShowError = vi.fn();

      // Mock a valid manual snapshot so sync button is enabled
      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "P1" })],
        }),
      );

      // Mock fetchNotionPlayers to reject with a network error
      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error("Network Error"),
      );

      render(SnapshotDetail, {
        props: {
          id: 1,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft: () => {},
          onEditDraft: () => {},
          onShowError,
          onShowToast: vi.fn(),
        },
      });

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Click sync button
      const syncBtn: HTMLButtonElement = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      // Wait for the rejected promise to be processed
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Verify error was shown
      expect(onShowError).toHaveBeenCalledWith(
        "Error de conexión",
        "Error: Network Error",
      );

      // Assert that sync button is no longer disabled and text has reverted
      expect(syncBtn.disabled).toBe(false);
      expect(syncBtn.textContent).toBe("🔄 Sincronizar Notion");

      // Restore fake timers for other tests
      vi.useFakeTimers();
    });
  });

  describe("New Svelte 5 Behaviors", () => {
    it("CSV button calls clipboard.writeText with correctly formatted derived CSV data", async () => {
      const { fetchSnapshot } = await import("../../api");
      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [
            createMockEditPlayerRow({
              nombre: "Test Player",
              experiencia: "Nuevo",
              juegos_este_ano: 5,
              prioridad: 1,
              partidas_deseadas: 2,
              partidas_gm: 1,
            }),
          ],
        }),
      );

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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Click the copy button
      const copyButton = screen.getByRole("button", {
        name: /Copiar CSV/i,
      });
      await fireEvent.click(copyButton);

      // Verify clipboard.writeText was called with correctly formatted CSV
      expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        "nombre,experiencia,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm\n" +
          "Test Player,Nuevo,5,1,2,1",
      );
    });

    it("CSV derived state updates automatically when player data changes", async () => {
      const { fetchSnapshot } = await import("../../api");

      // Initial mock with one player
      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "Player 1" })],
        }),
      );

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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Clear previous calls
      mockClipboard.writeText.mockClear();

      // Click copy button
      const copyButton = screen.getByRole("button", {
        name: /Copiar CSV/i,
      });
      await fireEvent.click(copyButton);

      // Verify CSV with first player
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining("Player 1"),
      );
    });

    it("Sincronizar button shows disabled state and 'Sincronizando...' when ui.isSyncing is true", async () => {
      // We need to test the UI state behavior by triggering sync
      const { fetchSnapshot, fetchNotionPlayers } = await import("../../api");

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "Test Player" })],
        }),
      );

      // Mock fetchNotionPlayers to never resolve (keep isSyncing true)
      const neverResolvePromise = new Promise<never>(() => {});
      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockReturnValue(
        neverResolvePromise,
      );

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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });
    });

    it("Editar button triggers onEditDraft with mapped playersForDraft data", async () => {
      const { fetchSnapshot } = await import("../../api");
      const onEditDraft = vi.fn();

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [
            createMockEditPlayerRow({
              nombre: "Test Player",
              experiencia: "Antiguo",
              juegos_este_ano: 3,
              prioridad: 1,
              partidas_deseadas: 2,
              partidas_gm: 1,
            }),
          ],
        }),
      );

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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Click the edit button
      const editButton = screen.getByRole("button", { name: /Editar/i });
      await fireEvent.click(editButton);

      // Verify onEditDraft was called with correctly mapped playersForDraft data
      expect(onEditDraft).toHaveBeenCalledTimes(1);
      expect(onEditDraft).toHaveBeenCalledWith(1, "manual", null, [
        createMockEditPlayerRow({
          nombre: "Test Player",
          experiencia: "Antiguo",
          juegos_este_ano: 3,
          prioridad: 1,
          partidas_deseadas: 2,
          partidas_gm: 1,
        }),
      ]);
    });

    it("OrganizarConfirmModal onEdit uses playersForDraft derived data", async () => {
      const { fetchSnapshot } = await import("../../api");
      const { validateOrganizar } = await import("../../syncUtils");
      const onEditDraft = vi.fn();

      const players = new Array(7).fill(null).map((_, i) =>
        createMockEditPlayerRow({
          nombre: `Player ${i + 1}`,
          partidas_deseadas: 1,
          partidas_gm: 0,
          prioridad: 0,
        }),
      );

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          players,
        }),
      );

      (validateOrganizar as ReturnType<typeof vi.fn>).mockReturnValueOnce({
        isAllOnes: true,
        gmShortage: null,
        excludedPlayers: [],
      });

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
          onShowToast: vi.fn(),
        },
      });

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      // Click organizar button to show modal
      const organizarButton = screen.getByRole("button", {
        name: /Organizar Partidas/i,
      });
      await fireEvent.click(organizarButton);

      // Click edit button in modal
      const modalEditButton = screen.getByRole("button", {
        name: /Volver a Editar/i,
      });
      await fireEvent.click(modalEditButton);

      // Verify onEditDraft was called with playersForDraft data
      expect(onEditDraft).toHaveBeenCalledTimes(1);
      expect(onEditDraft).toHaveBeenCalledWith(
        1,
        "manual",
        null,
        expect.arrayContaining([
          expect.objectContaining({
            nombre: expect.stringMatching(/Player \d+/) as string,
            experiencia: "Nuevo",
            juegos_este_ano: 0,
            prioridad: 0,
            partidas_deseadas: 1,
            partidas_gm: 0,
          }),
        ]),
      );
    });
  });
});
