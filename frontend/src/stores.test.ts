import { describe, it, expect, beforeEach } from "vitest";
import {
  setSnapshotCount,
  setChainData,
  getChainData,
  setActiveNodeId,
  getActiveNodeId,
} from "./stores.svelte";

describe("stores.svelte", () => {
  beforeEach(() => {
    setSnapshotCount(0);
    setChainData({ roots: [] });
    setActiveNodeId(null);
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
      setActiveNodeId(123);
      expect(getActiveNodeId()).toBe(123);
    });

    it("setActiveNodeId(null) clears the value", () => {
      setActiveNodeId(123);
      setActiveNodeId(null);
      expect(getActiveNodeId()).toBeNull();
    });
  });
});
