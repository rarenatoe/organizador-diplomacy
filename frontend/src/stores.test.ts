import { describe, it, expect, beforeEach } from "vitest";
import {
  getSelectedSnapshot,
  setSelectedSnapshot,
  deselectSnapshot,
  setSnapshotCount,
  getSyncButtonEnabled,
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
