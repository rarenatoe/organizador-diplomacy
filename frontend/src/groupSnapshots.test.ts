import { describe, it, expect } from "vitest";
import { groupSnapshots } from "./groupSnapshots";
import type { SnapshotNode, SyncEdge, EditEdge, GameEdge } from "./types";

describe("groupSnapshots", () => {
  const createSnapshot = (
    id: number,
    branches: SnapshotNode["branches"] = [],
  ): SnapshotNode => ({
    type: "snapshot",
    id,
    created_at: `2024-01-0${id}`,
    source: "manual",
    player_count: 5,
    is_latest: id === 1,
    branches,
  });

  const createSyncEdge = (id: number, from: number, to: number): SyncEdge => ({
    type: "sync",
    id,
    created_at: "2024-01-01",
    from_id: from,
    to_id: to,
  });

  const createEditEdge = (id: number, from: number, to: number): EditEdge => ({
    type: "edit",
    id,
    created_at: "2024-01-01",
    from_id: from,
    to_id: to,
  });

  const createGameEdge = (id: number, from: number, to: number): GameEdge => ({
    type: "game",
    id,
    created_at: "2024-01-01",
    from_id: from,
    to_id: to,
    intentos: 1,
    mesa_count: 3,
    espera_count: 0,
  });

  describe("single snapshot", () => {
    it("creates a group with one version for a standalone snapshot", () => {
      const root = createSnapshot(1);
      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(1);
      expect(group.versions[0]!.snapshot.id).toBe(1);
      expect(group.versions[0]!.incomingEdge).toBeNull();
      expect(group.branches).toEqual([]);
    });
  });

  describe("linear sync/edit chain", () => {
    it("groups a snapshot with a single sync child", () => {
      const child = createSnapshot(2);
      const root = createSnapshot(1, [
        { edge: createSyncEdge(10, 1, 2), output: child },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(2);
      expect(group.versions[0]!.snapshot.id).toBe(1);
      expect(group.versions[0]!.incomingEdge).toBeNull();
      expect(group.versions[1]!.snapshot.id).toBe(2);
      expect(group.versions[1]!.incomingEdge?.type).toBe("sync");
      expect(group.branches).toEqual([]);
    });

    it("groups a snapshot with a single edit child", () => {
      const child = createSnapshot(2);
      const root = createSnapshot(1, [
        { edge: createEditEdge(10, 1, 2), output: child },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(2);
      expect(group.versions[1]!.incomingEdge?.type).toBe("edit");
    });

    it("groups a chain of multiple sync/edit events", () => {
      const grandchild = createSnapshot(3);
      const child = createSnapshot(2, [
        { edge: createEditEdge(11, 2, 3), output: grandchild },
      ]);
      const root = createSnapshot(1, [
        { edge: createSyncEdge(10, 1, 2), output: child },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(3);
      expect(group.versions[0]!.snapshot.id).toBe(1);
      expect(group.versions[1]!.snapshot.id).toBe(2);
      expect(group.versions[2]!.snapshot.id).toBe(3);
    });
  });

  describe("game edge breaks grouping", () => {
    it("does not group when child is connected via game edge", () => {
      const child = createSnapshot(2);
      const root = createSnapshot(1, [
        { edge: createGameEdge(10, 1, 2), output: child },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(1);
      expect(group.versions[0]!.snapshot.id).toBe(1);
      expect(group.branches).toHaveLength(1);
      expect(group.branches[0]!.edge.type).toBe("game");
      expect(group.branches[0]!.output?.id).toBe(2);
    });
  });

  describe("multiple branches break grouping", () => {
    it("does not group when snapshot has multiple branches", () => {
      const child1 = createSnapshot(2);
      const child2 = createSnapshot(3);
      const root = createSnapshot(1, [
        { edge: createSyncEdge(10, 1, 2), output: child1 },
        { edge: createEditEdge(11, 1, 3), output: child2 },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(1);
      expect(group.branches).toHaveLength(2);
    });
  });

  describe("initialIncomingEdge", () => {
    it("sets incomingEdge on the first version when provided", () => {
      const root = createSnapshot(1);
      const incomingEdge = createSyncEdge(99, 0, 1);

      const result = groupSnapshots([root], incomingEdge);

      expect(result[0]!.versions[0]!.incomingEdge).toBe(incomingEdge);
    });

    it("preserves incomingEdge through the group chain", () => {
      const child = createSnapshot(2);
      const root = createSnapshot(1, [
        { edge: createEditEdge(10, 1, 2), output: child },
      ]);
      const incomingEdge = createSyncEdge(99, 0, 1);

      const result = groupSnapshots([root], incomingEdge);

      expect(result[0]!.versions[0]!.incomingEdge).toBe(incomingEdge);
      expect(result[0]!.versions[1]!.incomingEdge?.type).toBe("edit");
    });
  });

  describe("multiple roots", () => {
    it("creates separate groups for each root", () => {
      const root1 = createSnapshot(1);
      const root2 = createSnapshot(2);

      const result = groupSnapshots([root1, root2]);

      expect(result).toHaveLength(2);
      expect(result[0]!.versions[0]!.snapshot.id).toBe(1);
      expect(result[1]!.versions[0]!.snapshot.id).toBe(2);
    });
  });

  describe("complex tree", () => {
    it("handles a tree with sync chain and game branch", () => {
      // Root -> sync -> child -> game -> grandchild
      const grandchild = createSnapshot(3);
      const child = createSnapshot(2, [
        { edge: createGameEdge(11, 2, 3), output: grandchild },
      ]);
      const root = createSnapshot(1, [
        { edge: createSyncEdge(10, 1, 2), output: child },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      // Root and child should be grouped (sync edge)
      expect(group.versions).toHaveLength(2);
      expect(group.versions[0]!.snapshot.id).toBe(1);
      expect(group.versions[1]!.snapshot.id).toBe(2);
      // Grandchild should be in branches (game edge)
      expect(group.branches).toHaveLength(1);
      expect(group.branches[0]!.edge.type).toBe("game");
    });

    it("handles multiple branches after a grouped chain", () => {
      // Root -> sync -> child -> (game -> g1, edit -> g2)
      const g1 = createSnapshot(3);
      const g2 = createSnapshot(4);
      const child = createSnapshot(2, [
        { edge: createGameEdge(11, 2, 3), output: g1 },
        { edge: createEditEdge(12, 2, 4), output: g2 },
      ]);
      const root = createSnapshot(1, [
        { edge: createSyncEdge(10, 1, 2), output: child },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(2);
      expect(group.branches).toHaveLength(2);
    });
  });

  describe("edge cases", () => {
    it("handles empty roots array", () => {
      const result = groupSnapshots([]);
      expect(result).toEqual([]);
    });

    it("handles snapshot with null output in branch", () => {
      const root = createSnapshot(1, [
        { edge: createSyncEdge(10, 1, 2), output: null },
      ]);

      const result = groupSnapshots([root]);

      expect(result).toHaveLength(1);
      const group = result[0]!;
      expect(group.versions).toHaveLength(1);
      expect(group.branches).toHaveLength(1);
      expect(group.branches[0]!.output).toBeNull();
    });
  });
});
