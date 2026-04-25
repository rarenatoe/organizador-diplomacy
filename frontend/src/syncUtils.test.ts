// ── Sync Utilities Tests ──────────────────────────────────────────────
import { describe, expect, it } from "vitest";

import type { NotionPlayerData } from "./generated-api";
import { MergePair } from "./syncResolution";
import { applySyncMerges } from "./syncUtils";
import type { EditPlayerRow } from "./types";

const createNotionPlayer = (
  overrides: Partial<NotionPlayerData> = {},
): NotionPlayerData => ({
  notion_id: "notion_123",
  nombre: "Notion Name",
  is_new: false,
  juegos_este_ano: 5,
  c_england: 0,
  c_france: 0,
  c_germany: 0,
  c_italy: 0,
  c_austria: 0,
  c_russia: 0,
  c_turkey: 0,
  alias: ["alias1", "alias2"],
  ...overrides,
});

describe("applySyncMerges", () => {
  const mockNotionPlayers: NotionPlayerData[] = [createNotionPlayer()];

  describe("Edge Case 1: Standard Deduplication", () => {
    it("should deduplicate identical names", () => {
      const currentRows: EditPlayerRow[] = [
        {
          nombre: "Duplicate Name",
          is_new: true,
          juegos_este_ano: 0,
          has_priority: true,
          partidas_deseadas: 1,
          partidas_gm: 0,
          notion_id: null,
          notion_name: null,
        },
        {
          nombre: "Duplicate Name",
          is_new: false,
          juegos_este_ano: 3,
          has_priority: false,
          partidas_deseadas: 2,
          partidas_gm: 1,
          notion_id: null,
          notion_name: null,
        },
      ];

      const result = applySyncMerges(currentRows, [], mockNotionPlayers);

      // Should only contain ONE row with "Duplicate Name"
      const duplicateNames = result.filter(
        (row) => row.nombre === "Duplicate Name",
      );
      expect(duplicateNames).toHaveLength(1);

      // Should keep the first occurrence (or merge with Notion data if available)
      expect(result).toHaveLength(1);
      expect(result[0]?.nombre).toBe("Duplicate Name");
    });
  });

  describe("Edge Case 2: 'use_existing' action", () => {
    it("should use existing local name when action is 'use_existing'", () => {
      const currentRows: EditPlayerRow[] = [
        {
          nombre: "Typo Name",
          is_new: true,
          juegos_este_ano: 0,
          has_priority: true,
          partidas_deseadas: 1,
          partidas_gm: 0,
          notion_id: null,
          notion_name: null,
        },
      ];

      const merges: MergePair[] = [
        {
          from: "Typo Name",
          to: "Local Name",
          action: "use_existing",
        },
      ];

      const result = applySyncMerges(currentRows, merges, mockNotionPlayers);

      // Should rename to "Local Name"
      expect(result).toHaveLength(1);
      expect(result[0]?.nombre).toBe("Local Name");
      expect(result[0]?.is_new).toBe(true); // Keep local data
      expect(result[0]?.juegos_este_ano).toBe(0);
    });
  });

  describe("Edge Case 3: 'link_rename' action", () => {
    it("should rename to Notion name and attach notion_id when action is 'link_rename'", () => {
      const currentRows: EditPlayerRow[] = [
        {
          nombre: "Local",
          is_new: true,
          juegos_este_ano: 0,
          has_priority: true,
          partidas_deseadas: 1,
          partidas_gm: 0,
          notion_id: null,
          notion_name: null,
        },
      ];

      const merges: MergePair[] = [
        {
          from: "Local",
          to: "Notion Name",
          action: "link_rename",
        },
      ];

      const result = applySyncMerges(currentRows, merges, mockNotionPlayers);

      // Should rename to "Notion Name" AND attach notion_id
      expect(result).toHaveLength(1);
      expect(result[0]?.nombre).toBe("Notion Name");
      expect(result[0]?.notion_id).toBe("notion_123");
      expect(result[0]?.notion_name).toBe("Notion Name");
      expect(result[0]?.is_new).toBe(false); // Use Notion data
      expect(result[0]?.juegos_este_ano).toBe(5); // Use Notion data
    });
  });

  describe("Edge Case 4: 'link_only' action", () => {
    it("should attach notion_id without renaming when action is 'link_only'", () => {
      const currentRows: EditPlayerRow[] = [
        {
          nombre: "Local Name",
          is_new: true,
          juegos_este_ano: 0,
          has_priority: true,
          partidas_deseadas: 1,
          partidas_gm: 0,
          notion_id: null,
          notion_name: null,
        },
      ];

      const merges: MergePair[] = [
        {
          from: "Local Name",
          to: "Notion Name",
          action: "link_only",
        },
      ];

      const result = applySyncMerges(currentRows, merges, mockNotionPlayers);

      // Should NOT rename, but should attach notion_id
      expect(result).toHaveLength(1);
      expect(result[0]?.nombre).toBe("Local Name"); // Keep local name
      expect(result[0]?.notion_id).toBe("notion_123"); // But attach notion_id
      expect(result[0]?.notion_name).toBe("Notion Name");
      expect(result[0]?.is_new).toBe(false); // Use Notion data
      expect(result[0]?.juegos_este_ano).toBe(5); // Use Notion data
    });
  });

  describe("Edge Case 5: Unmatched Players Pass Through", () => {
    it("should pass through players with no merges and no Notion match unmodified", () => {
      const currentRows: EditPlayerRow[] = [
        {
          nombre: "Unmatched Player",
          is_new: true,
          juegos_este_ano: 0,
          has_priority: true,
          partidas_deseadas: 1,
          partidas_gm: 0,
          notion_id: null,
          notion_name: null,
        },
      ];

      const merges: MergePair[] = []; // No merges
      const emptyNotionPlayers: NotionPlayerData[] = []; // No Notion matches

      const result = applySyncMerges(currentRows, merges, emptyNotionPlayers);

      // Should pass through completely unmodified
      expect(result).toHaveLength(1);
      expect(result[0]?.nombre).toBe("Unmatched Player");
      expect(result[0]?.is_new).toBe(true);
      expect(result[0]?.juegos_este_ano).toBe(0);
      expect(result[0]?.has_priority).toBe(true);
      expect(result[0]?.partidas_deseadas).toBe(1);
      expect(result[0]?.partidas_gm).toBe(0);
      expect(result[0]?.notion_id).toBe(null);
      expect(result[0]?.notion_name).toBe(null);
    });
  });
});
