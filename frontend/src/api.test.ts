import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { EditPlayerRow } from "./types";
import {
  fetchChain,
  fetchSnapshot,
  deleteSnapshot,
  createSnapshot,
  saveSnapshot,
  fetchNotionPlayers,
  fetchGame,
  fetchGameDraft,
  saveGameDraft,
  deleteGame,
  renamePlayer,
} from "./api";

describe("api.ts - FastAPI Error Handling", () => {
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn();
    globalThis.fetch = mockFetch as typeof globalThis.fetch;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("successful responses", () => {
    it("returns parsed JSON for 200 OK", async () => {
      const mockData = { id: 1, name: "Test" };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockData),
      } as Response);

      const result = await fetchChain();
      expect(result).toEqual(mockData);
    });

    it("returns parsed JSON for 201 Created", async () => {
      const mockData = { success: true, id: 123 };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve(mockData),
      } as Response);

      const result = await createSnapshot([
        {
          nombre: "Test",
          is_new: false,
          has_priority: true,
          partidas_deseadas: 2,
          partidas_gm: 0,
        },
      ]);
      expect(result).toEqual(mockData);
    });
  });

  describe("422 validation error handling", () => {
    it("extracts and joins error messages from detail array", async () => {
      const errorResponse = {
        detail: [
          { loc: ["body", "name"], msg: "Field required", type: "missing" },
          { loc: ["body", "age"], msg: "Invalid integer", type: "type_error" },
        ],
      };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await saveSnapshot({
        parent_id: 1,
        event_type: "sync",
        players: [],
      });

      expect(result).toEqual({ error: "Field required; Invalid integer" });
    });

    it("handles single validation error", async () => {
      const errorResponse = {
        detail: [
          {
            loc: ["body", "players"],
            msg: "At least one player required",
            type: "value_error",
          },
        ],
      };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await createSnapshot([]);
      expect(result).toEqual({ error: "At least one player required" });
    });

    it("handles empty detail array gracefully", async () => {
      const errorResponse = { detail: [] };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchNotionPlayers([]);
      expect(result).toEqual({ error: "Conflict", detail: [] });
    });
  });

  describe("HTTPException error handling (detail as string)", () => {
    it("normalizes detail string to error field", async () => {
      const errorResponse = { detail: "Snapshot not found" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchSnapshot(999);
      expect(result).toEqual({ error: "Snapshot not found" });
    });

    it("handles 500 Internal Server Error with detail", async () => {
      const errorResponse = { detail: "Database connection failed" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchGame(1);
      expect(result).toEqual({ error: "Database connection failed" });
    });

    it("handles 400 Bad Request with detail", async () => {
      const errorResponse = { detail: "Invalid request parameters" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchGameDraft(1);
      expect(result).toEqual({ error: "Invalid request parameters" });
    });
  });

  describe("fallback error handling", () => {
    it("uses data.error when available", async () => {
      const errorResponse = { error: "Custom error message" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await deleteSnapshot(1);
      expect(result).toEqual({ error: "Custom error message" });
    });

    it("falls back to generic error message", async () => {
      const errorResponse = {};
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 418,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await saveGameDraft({
        snapshot_id: 1,
        draft: {
          mesas: [],
          tickets_sobrantes: [],
          minimo_teorico: 1,
          intentos_usados: 0,
        },
      });
      expect(result).toEqual({ error: "Error de servidor" });
    });

    it("handles malformed error response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve(null),
      } as Response);

      const result = await renamePlayer("Old", "New");
      expect(result).toEqual({ error: "Error de servidor" });
    });
  });

  describe("all API functions use safeFetch", () => {
    it("fetchChain uses safeFetch error handling", async () => {
      const errorResponse = { detail: "Server error" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchChain();
      expect(result).toEqual({ error: "Server error" });
    });

    it("fetchSnapshot uses safeFetch error handling", async () => {
      const errorResponse = {
        detail: [
          {
            loc: ["path", "id"],
            msg: "Invalid snapshot ID",
            type: "type_error",
          },
        ],
      };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchSnapshot(1);
      expect(result).toEqual({ error: "Invalid snapshot ID" });
    });

    it("saveSnapshot handles 422 validation errors", async () => {
      const errorResponse = {
        detail: [
          {
            loc: ["body", "event_type"],
            msg: "Invalid event type",
            type: "enum",
          },
        ],
      };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await saveSnapshot({
        parent_id: 1,
        event_type: "invalid",
        players: [],
      });
      expect(result).toEqual({ error: "Invalid event type" });
    });

    it("fetchGameDraft handles validation errors", async () => {
      const errorResponse = {
        detail: [
          {
            loc: ["body", "snapshot_id"],
            msg: "Snapshot not found",
            type: "not_found",
          },
        ],
      };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchGameDraft(999);
      expect(result).toEqual({ error: "Snapshot not found" });
    });

    it("saveGameDraft normalizes HTTPException errors", async () => {
      const errorResponse = { detail: "Failed to save game" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await saveGameDraft({
        snapshot_id: 1,
        draft: {
          mesas: [],
          tickets_sobrantes: [],
          minimo_teorico: 1,
          intentos_usados: 0,
        },
      });
      expect(result).toEqual({ error: "Failed to save game" });
    });

    it("renamePlayer returns error object on failure", async () => {
      const errorResponse = { detail: "Player not found" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await renamePlayer("Old", "New");
      expect(result).toEqual({ error: "Player not found" });
    });
  });

  describe("Flask vs FastAPI error format compatibility", () => {
    it("handles Flask-style {error: string} format", async () => {
      // Legacy format - some endpoints might still return this
      const errorResponse = { error: "Legacy error format" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await deleteSnapshot(1);
      expect(result).toEqual({ error: "Legacy error format" });
    });

    it("prioritizes FastAPI detail over error field when both present", async () => {
      // Shouldn't happen, but test behavior
      const errorResponse = { detail: "FastAPI error", error: "Flask error" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchSnapshot(1);
      // Detail (FastAPI format) should be used first
      expect(result).toEqual({ error: "FastAPI error" });
    });
  });

  describe("type guard edge cases (regression prevention)", () => {
    it("handles detail as non-array (malformed validation error)", async () => {
      // Server sends detail that's not an array - should fall back
      const errorResponse = { detail: "not an array" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchSnapshot(1);
      expect(result).toEqual({ error: "not an array" });
    });

    it("handles detail array with malformed objects (missing msg field)", async () => {
      const errorResponse = {
        detail: [{ loc: ["body"], type: "missing" }] as unknown,
      };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await createSnapshot([]);
      expect(result).toEqual({
        error: "Conflict",
        detail: [{ loc: ["body"], type: "missing" }],
      });
    });

    it("handles response without detail or error fields", async () => {
      // Response has neither detail nor error (only other fields)
      const errorResponse = { message: "something" };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await fetchGame(1);
      expect(result).toEqual({ error: "Error de servidor" });
    });

    it("handles response with null or undefined detail", async () => {
      const errorResponse = { detail: null };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve(errorResponse),
      } as Response);

      const result = await renamePlayer("Old", "New");
      expect(result).toEqual({ error: "Error de servidor" });
    });
  });

  describe("API endpoint correctness (regression prevention)", () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      } as Response);
    });

    it("fetchChain calls /api/chain with GET", async () => {
      await fetchChain();
      expect(mockFetch).toHaveBeenCalledWith("/api/chain", undefined);
    });

    it("fetchSnapshot calls /api/snapshot/:id with GET", async () => {
      await fetchSnapshot(123);
      expect(mockFetch).toHaveBeenCalledWith("/api/snapshot/123", undefined);
    });

    it("deleteSnapshot calls /api/snapshot/:id with DELETE", async () => {
      await deleteSnapshot(456);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/snapshot/456",
        expect.objectContaining({ method: "DELETE" }),
      );
    });

    it("createSnapshot calls /api/snapshot/new with POST", async () => {
      const players: EditPlayerRow[] = [
        {
          nombre: "Test",
          is_new: false,
          has_priority: true,
          partidas_deseadas: 2,
          partidas_gm: 0,
        },
      ];
      await createSnapshot(players);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/snapshot/new",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ players }),
        }),
      );
    });

    it("saveSnapshot calls /api/snapshot/save with POST", async () => {
      const payload = {
        parent_id: 1,
        event_type: "sync",
        players: [],
      };
      await saveSnapshot(payload);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/snapshot/save",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(payload),
        }),
      );
    });

    it("fetchNotionPlayers calls /api/snapshot/notion/fetch with POST", async () => {
      await fetchNotionPlayers(["snapshot1"]);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/snapshot/notion/fetch",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ snapshot_names: ["snapshot1"] }),
        }),
      );
    });

    it("fetchGame calls /api/game/:id with GET", async () => {
      await fetchGame(789);
      expect(mockFetch).toHaveBeenCalledWith("/api/game/789", undefined);
    });

    it("fetchGameDraft calls /api/game/draft with POST", async () => {
      await fetchGameDraft(111);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/game/draft",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ snapshot_id: 111 }),
        }),
      );
    });

    it("saveGameDraft calls /api/game/save with POST", async () => {
      const request = {
        snapshot_id: 222,
        draft: {
          mesas: [],
          tickets_sobrantes: [],
          minimo_teorico: 1,
          intentos_usados: 0,
        },
      };
      await saveGameDraft(request);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/game/save",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(request),
        }),
      );
    });

    it("renamePlayer calls /api/player/rename with POST", async () => {
      await renamePlayer("OldName", "NewName");
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/player/rename",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ old_name: "OldName", new_name: "NewName" }),
        }),
      );
    });

    it("deleteGame sends DELETE to /api/games/:id", async () => {
      await deleteGame(123);
      expect(mockFetch).toHaveBeenCalledWith("/api/game/123", {
        method: "DELETE",
      });
    });
  });
});
