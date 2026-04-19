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
  applySyncMerges: vi.fn(),
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
            is_new: false,
            juegos_este_ano: 3,
            has_priority: true,
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
    const { container } = await renderSnapshotDetail();

    // Assert structural hierarchy - major content blocks should be wrapped in .section divs
    expect(container.querySelector(".section")).toBeInTheDocument();

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
        is_new: false,
        juegos_este_ano: 3,
        has_priority: true,
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

  it("handles CSV export formatting and UI copy feedback", async () => {
    await renderSnapshotDetail();

    const copyButton = screen.getByText("Copiar CSV");
    await fireEvent.click(copyButton);

    // Verify clipboard.writeText was called with exact payload
    expect(mockClipboard.writeText).toHaveBeenCalledTimes(1);
    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      "nombre,is_new,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm\n" +
        "P1,Nuevo,0,false,1,0\n" +
        "P2,Antiguo,3,true,2,1\n" +
        "P3,Nuevo,0,false,1,0\n" +
        "P4,Nuevo,0,false,1,0\n" +
        "P5,Nuevo,0,false,1,0\n" +
        "P6,Nuevo,0,false,1,0\n" +
        "P7,Nuevo,0,false,1,0",
    );

    // Verify button changes to "Copiado"
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

  it("should allow Sincronizar Notion and fetch players regardless of source", async () => {
    const { fetchSnapshot, fetchNotionPlayers } = await import("../../api");
    (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockSnapshotDetail({
        id: 4,
        source: "notion_sync", // Test with notion_sync to prove frontend doesn't block
        created_at: "2024-01-01 12:00:00",
        players: [createMockEditPlayerRow({ nombre: "P1" })],
      }),
    );

    const onShowError = vi.fn();
    const onShowToast = vi.fn();

    await renderSnapshotDetail({ id: 4, onShowError, onShowToast });

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.queryByText("Cargando…")).toBeNull();
    });

    // Click "Sincronizar Notion"
    const syncBtn = screen.getByText(/Sincronizar Notion/);
    await fireEvent.click(syncBtn);

    // Assert sync proceeds: fetchNotionPlayers called, no frontend error
    expect(fetchNotionPlayers).toHaveBeenCalledWith(["P1"]);
    expect(onShowError).not.toHaveBeenCalled();
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
          has_priority: false,
          is_new: true,
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

    it("handles notion sync merge with renames payload and snapshot reload", async () => {
      // Use real timers for this test to avoid async issues
      vi.useRealTimers();

      const { fetchSnapshot, fetchNotionPlayers, saveSnapshot } =
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
                is_new: false,
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
            is_new: false,
            juegos_este_ano: 5,
          }),
        ],
        similar_names: [
          { notion: "Renato Alegre", snapshot: "Renato", similarity: 0.85 },
        ],
        error: undefined,
      });

      // Mock renamePlayer and saveSnapshot to succeed
      (saveSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        snapshot_id: 2,
      });

      // Mock applySyncMerges to return expected renames
      const { applySyncMerges } = await import("../../syncUtils");
      (applySyncMerges as ReturnType<typeof vi.fn>).mockReturnValueOnce([
        { from: "Renato", to: "Renato Alegre" },
      ]);

      await renderSnapshotDetail({ id: 1, onOpenSnapshot });

      // Click sync button to trigger the sync
      const syncBtn = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      // Wait for the resolution modal to appear
      await waitFor(() => {
        expect(screen.getByText(/Resolver Conflictos/i)).toBeTruthy();
      });

      // Click "Vincular & Renombrar" button to trigger merge
      const notionBtn = screen.getByRole("button", {
        name: /Vincular & Renombrar/i,
      });
      await fireEvent.click(notionBtn);

      // Wait for the async operations to complete
      await waitFor(() => {
        expect(saveSnapshot).toHaveBeenCalled();
      });

      // Verify saveSnapshot was called with the correct renames payload
      expect(saveSnapshot).toHaveBeenCalledWith(
        expect.objectContaining({
          renames: [{ from: "Renato", to: undefined }],
        }),
      );

      // Verify fetchSnapshot was called again (reload after save)
      await waitFor(() => {
        expect(fetchSnapshot).toHaveBeenCalledTimes(2);
      });

      // Restore fake timers
      vi.useFakeTimers();
    });

    it("should reset isSyncing state on API payload errors", async () => {
      vi.useRealTimers(); // Fixes the 5000ms deadlock

      const { fetchSnapshot, fetchNotionPlayers, saveSnapshot } =
        await import("../../api");
      const onShowError = vi.fn();

      // Test error from fetchNotionPlayers
      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 1,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "P1" })],
        }),
      );

      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        error: "API limit reached",
        players: [],
        similar_names: [],
      });

      const { unmount } = render(SnapshotDetail, {
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

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const syncBtn: HTMLButtonElement = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      await waitFor(() => {
        expect(onShowError).toHaveBeenCalledWith(
          "Error de Sincronización",
          "API limit reached",
        );
      });

      expect(syncBtn.disabled).toBe(false);
      expect(syncBtn.textContent).toBe("🔄 Sincronizar Notion");
      unmount();

      // Test error from saveSnapshot
      vi.clearAllMocks();
      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 2,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "P2" })],
        }),
      );

      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        players: [],
        similar_names: [],
        error: undefined,
      });

      (saveSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        error: "Backend strict guard rejected save",
      });

      render(SnapshotDetail, {
        props: {
          id: 2,
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

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const syncBtn2: HTMLButtonElement = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn2);

      // Flush async API chain
      const { tick } = await import("svelte");
      await tick();
      await new Promise((r) => setTimeout(r, 0));
      await tick();

      await waitFor(() => {
        expect(onShowError).toHaveBeenCalledWith(
          "Error de Sincronización",
          "Backend strict guard rejected save",
        );
      });

      expect(syncBtn2.disabled).toBe(false);
      expect(syncBtn2.textContent).toBe("🔄 Sincronizar Notion");
    });

    it("should reset isSyncing state on network exceptions", async () => {
      vi.useRealTimers();

      const { fetchSnapshot, fetchNotionPlayers } = await import("../../api");
      const onShowError = vi.fn();

      (fetchSnapshot as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockSnapshotDetail({
          id: 3,
          created_at: "2024-01-01T00:00:00Z",
          source: "manual",
          players: [createMockEditPlayerRow({ nombre: "P3" })],
        }),
      );

      (fetchNotionPlayers as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error("Network Error"),
      );

      render(SnapshotDetail, {
        props: {
          id: 3,
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

      await waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const syncBtn: HTMLButtonElement = screen.getByRole("button", {
        name: /Sincronizar Notion/i,
      });
      await fireEvent.click(syncBtn);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(onShowError).toHaveBeenCalledWith(
        "Error de conexión",
        "Error: Network Error",
      );
      expect(syncBtn.disabled).toBe(false);
      expect(syncBtn.textContent).toBe("🔄 Sincronizar Notion");

      vi.useFakeTimers();
    });
  });
});
