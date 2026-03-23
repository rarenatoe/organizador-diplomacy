import { describe, it, expect } from "vitest";
import { findLatestSnapshotId, findLatestGameId } from "./snapshotUtils";
import type { SnapshotNode, GameEdge, SyncEdge } from "./types";

describe("snapshotUtils", () => {
  const createSnapshot = (
    id: number,
    isLatest: boolean,
    branches: SnapshotNode["branches"] = [],
  ): SnapshotNode => ({
    type: "snapshot",
    id,
    created_at: `2024-01-0${id}`,
    source: "manual",
    player_count: 5,
    is_latest: isLatest,
    branches,
  });

  const createGameEdge = (id: number, createdAt: string): GameEdge => ({
    type: "game",
    id,
    created_at: createdAt,
    from_id: 1,
    to_id: 2,
    intentos: 1,
    mesa_count: 3,
    espera_count: 0,
  });

  const createSyncEdge = (id: number): SyncEdge => ({
    type: "sync",
    id,
    created_at: "2024-01-01",
    from_id: 1,
    to_id: 2,
  });

  describe("findLatestSnapshotId", () => {
    it("returns null for undefined roots", () => {
      expect(findLatestSnapshotId(undefined)).toBeNull();
    });

    it("returns null for empty roots array", () => {
      expect(findLatestSnapshotId([])).toBeNull();
    });

    it("finds latest snapshot in a single root", () => {
      const root = createSnapshot(1, true);
      expect(findLatestSnapshotId([root])).toBe(1);
    });

    it("finds latest snapshot when multiple roots exist", () => {
      const root1 = createSnapshot(1, false);
      const root2 = createSnapshot(2, true);
      expect(findLatestSnapshotId([root1, root2])).toBe(2);
    });

    it("finds latest snapshot in nested branches", () => {
      const child = createSnapshot(3, true);
      const root = createSnapshot(1, false, [
        { edge: createSyncEdge(10), output: child },
      ]);
      expect(findLatestSnapshotId([root])).toBe(3);
    });

    it("finds latest snapshot in deeply nested branches", () => {
      const grandchild = createSnapshot(4, true);
      const child = createSnapshot(3, false, [
        { edge: createSyncEdge(11), output: grandchild },
      ]);
      const root = createSnapshot(1, false, [
        { edge: createSyncEdge(10), output: child },
      ]);
      expect(findLatestSnapshotId([root])).toBe(4);
    });

    it("returns last found when multiple snapshots have is_latest true", () => {
      const child = createSnapshot(2, true);
      const root = createSnapshot(1, true, [
        { edge: createSyncEdge(10), output: child },
      ]);
      // Should return the last one found (child)
      expect(findLatestSnapshotId([root])).toBe(2);
    });

    it("handles branches with null output", () => {
      const root = createSnapshot(1, true, [
        { edge: createSyncEdge(10), output: null },
      ]);
      expect(findLatestSnapshotId([root])).toBe(1);
    });
  });

  describe("findLatestGameId", () => {
    it("returns null for undefined roots", () => {
      expect(findLatestGameId(undefined)).toBeNull();
    });

    it("returns null for empty roots array", () => {
      expect(findLatestGameId([])).toBeNull();
    });

    it("returns null when no game edges exist", () => {
      const root = createSnapshot(1, true);
      expect(findLatestGameId([root])).toBeNull();
    });

    it("finds latest game by timestamp", () => {
      const child = createSnapshot(2, false);
      const root = createSnapshot(1, true, [
        {
          edge: createGameEdge(10, "2024-01-01T10:00:00"),
          output: child,
        },
      ]);
      expect(findLatestGameId([root])).toBe(10);
    });

    it("finds latest game when multiple games exist", () => {
      const child1 = createSnapshot(2, false);
      const child2 = createSnapshot(3, false);
      const root = createSnapshot(1, true, [
        {
          edge: createGameEdge(10, "2024-01-01T10:00:00"),
          output: child1,
        },
        {
          edge: createGameEdge(11, "2024-01-01T12:00:00"),
          output: child2,
        },
      ]);
      expect(findLatestGameId([root])).toBe(11);
    });

    it("finds latest game in nested branches", () => {
      const grandchild = createSnapshot(3, false);
      const child = createSnapshot(2, false, [
        {
          edge: createGameEdge(11, "2024-01-01T12:00:00"),
          output: grandchild,
        },
      ]);
      const root = createSnapshot(1, true, [
        {
          edge: createGameEdge(10, "2024-01-01T10:00:00"),
          output: child,
        },
      ]);
      expect(findLatestGameId([root])).toBe(11);
    });

    it("ignores non-game edges", () => {
      const child = createSnapshot(2, false);
      const root = createSnapshot(1, true, [
        { edge: createSyncEdge(10), output: child },
      ]);
      expect(findLatestGameId([root])).toBeNull();
    });

    it("handles mixed game and sync edges", () => {
      const child1 = createSnapshot(2, false);
      const child2 = createSnapshot(3, false);
      const root = createSnapshot(1, true, [
        { edge: createSyncEdge(10), output: child1 },
        {
          edge: createGameEdge(11, "2024-01-01T12:00:00"),
          output: child2,
        },
      ]);
      expect(findLatestGameId([root])).toBe(11);
    });

    it("handles branches with null output", () => {
      const root = createSnapshot(1, true, [
        {
          edge: createGameEdge(10, "2024-01-01T10:00:00"),
          output: null,
        },
      ]);
      expect(findLatestGameId([root])).toBe(10);
    });
  });
});
