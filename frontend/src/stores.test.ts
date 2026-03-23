import { describe, it, expect, beforeEach } from "vitest";
import {
  getSelectedSnapshot,
  setSelectedSnapshot,
  deselectSnapshot,
  setSnapshotCount,
  getSyncButtonEnabled,
  getOrganizarEnabled,
  getOrganizarLabel,
  setChainData,
  getChainData,
  setActiveNodeId,
  getActiveNodeId,
} from "./stores.svelte";

describe("stores.svelte", () => {
  beforeEach(() => {
    deselectSnapshot();
    setSnapshotCount(0);
    setChainData({ roots: [] });
    setActiveNodeId(null);
  });

  describe("selectedSnapshot", () => {
    it("starts as null", () => {
      expect(getSelectedSnapshot()).toBeNull();
    });

    it("setSelectedSnapshot sets the value", () => {
      setSelectedSnapshot(42);
      expect(getSelectedSnapshot()).toBe(42);
    });

    it("deselectSnapshot resets to null", () => {
      setSelectedSnapshot(42);
      deselectSnapshot();
      expect(getSelectedSnapshot()).toBeNull();
    });
  });

  describe("syncButtonEnabled", () => {
    it("getSyncButtonEnabled returns false when snapshotCount is -1 (loading state)", () => {
      setSnapshotCount(-1);
      expect(getSyncButtonEnabled()).toBe(false);
    });

    it("enabled when no snapshots exist", () => {
      setSnapshotCount(0);
      expect(getSyncButtonEnabled()).toBe(true);
    });

    it("disabled when snapshots exist but none selected", () => {
      setSnapshotCount(5);
      deselectSnapshot();
      expect(getSyncButtonEnabled()).toBe(false);
    });

    it("enabled when snapshot is selected", () => {
      setSnapshotCount(5);
      setSelectedSnapshot(1);
      expect(getSyncButtonEnabled()).toBe(true);
    });

    it("getSyncButtonEnabled returns false if data exists but none selected", () => {
      setSnapshotCount(10);
      deselectSnapshot();
      expect(getSyncButtonEnabled()).toBe(false);
    });

    it("deselectSnapshot() followed by setSnapshotCount(1) returns false", () => {
      deselectSnapshot();
      setSnapshotCount(1);
      expect(getSyncButtonEnabled()).toBe(false);
    });
  });

  describe("organizarEnabled", () => {
    it("disabled when no snapshot selected", () => {
      deselectSnapshot();
      expect(getOrganizarEnabled()).toBe(false);
    });

    it("enabled when snapshot is selected", () => {
      setSelectedSnapshot(42);
      expect(getOrganizarEnabled()).toBe(true);
    });

    it("getOrganizarEnabled returns false if no snapshot selected regardless of count", () => {
      setSnapshotCount(100);
      deselectSnapshot();
      expect(getOrganizarEnabled()).toBe(false);
    });
  });

  describe("organizarLabel with snapshot", () => {
    it("setSelectedSnapshot(123) returns 'Organizar · #123'", () => {
      setSelectedSnapshot(123);
      expect(getOrganizarLabel()).toBe("Organizar · #123");
    });
  });

  describe("organizarLabel", () => {
    it("shows 'Organizar' when no snapshot selected", () => {
      deselectSnapshot();
      expect(getOrganizarLabel()).toBe("Organizar");
    });

    it("shows snapshot ID when selected", () => {
      setSelectedSnapshot(42);
      expect(getOrganizarLabel()).toBe("Organizar · #42");
    });
  });

  describe("chainData", () => {
    it("starts as empty roots", () => {
      expect(getChainData()).toEqual({ roots: [] });
    });

    it("setChainData updates the value", () => {
      const data = {
        roots: [
          {
            type: "snapshot" as const,
            id: 1,
            created_at: "2024-01-01",
            source: "manual",
            player_count: 5,
            is_latest: true,
          },
        ],
      };
      setChainData(data);
      expect(getChainData()).toEqual(data);
    });
  });

  describe("activeNodeId", () => {
    it("starts as null", () => {
      expect(getActiveNodeId()).toBeNull();
    });

    it("setActiveNodeId sets the value", () => {
      setActiveNodeId("game-123");
      expect(getActiveNodeId()).toBe("game-123");
    });

    it("setActiveNodeId(null) clears the value", () => {
      setActiveNodeId("game-123");
      setActiveNodeId(null);
      expect(getActiveNodeId()).toBeNull();
    });
  });
});
