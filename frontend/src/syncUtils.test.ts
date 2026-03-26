// ── Sync Utilities Tests ──────────────────────────────────────────────────────

import { describe, it, expect } from "vitest";
import {
  normalizeName,
  wordsMatch,
  similarity,
  detectSimilarNames,
  calculateProjectedTables,
  checkGMShortage,
  validateOrganizar,
} from "./syncUtils";

describe("normalizeName", () => {
  it("should lowercase and trim whitespace", () => {
    expect(normalizeName("  John   Doe  ")).toBe("john doe");
    expect(normalizeName("JANE")).toBe("jane");
    expect(normalizeName("  Multiple   Spaces  ")).toBe("multiple spaces");
  });

  it("should handle empty strings", () => {
    expect(normalizeName("")).toBe("");
    expect(normalizeName("   ")).toBe("");
  });
});

describe("wordsMatch", () => {
  it("should match exact words", () => {
    expect(wordsMatch("John", "John")).toBe(true);
    expect(wordsMatch("john", "JOHN")).toBe(true);
  });

  it("should match when one word is a prefix of the other", () => {
    expect(wordsMatch("Ren", "Renato")).toBe(true);
    expect(wordsMatch("Renato", "Ren")).toBe(true);
    expect(wordsMatch("D", "Doe")).toBe(true);
  });

  it("should match abbreviated words with periods", () => {
    expect(wordsMatch("P.", "Paul")).toBe(true);
    expect(wordsMatch("Paul", "P.")).toBe(true);
    expect(wordsMatch("D.", "Doe")).toBe(true);
  });

  it("should not match unrelated words", () => {
    expect(wordsMatch("John", "Jane")).toBe(false);
    expect(wordsMatch("Alice", "Bob")).toBe(false);
  });

  it("should handle empty strings", () => {
    expect(wordsMatch("", "John")).toBe(false);
    expect(wordsMatch("John", "")).toBe(false);
    expect(wordsMatch("", "")).toBe(false);
  });
});

describe("similarity", () => {
  it("should return 1.0 for identical names", () => {
    expect(similarity("John Doe", "John Doe")).toBe(1.0);
    expect(similarity("john doe", "JOHN DOE")).toBe(1.0);
  });

  it("should return 1.0 when first name is a prefix", () => {
    expect(similarity("Ren Alegre", "Renato Alegre")).toBe(1.0);
  });

  it("should return 1.0 for abbreviated first names", () => {
    expect(similarity("P. Knight", "Paul Knight")).toBe(1.0);
  });

  it("should return 1.0 for abbreviated last names", () => {
    expect(similarity("Miguel P.", "Miguel Paucar")).toBe(1.0);
  });

  it("should return 1.0 when both names are abbreviated", () => {
    expect(similarity("T. Lopez", "Tomas L")).toBe(1.0);
  });

  it("should return 0.0 when names don't match", () => {
    expect(similarity("Chachi Faker", "Charlie Faker")).toBe(0.0);
    expect(similarity("Lori Sanchez", "Lori Sal.")).toBe(0.0);
    expect(similarity("Gonzalo Ch.", "Gonzalo L.")).toBe(0.0);
  });

  it("should handle different word counts with prefix matching (regression)", () => {
    // Jean Carlos (local) matches Jean Carlos R. (Notion) -> 0.8
    expect(similarity("Jean Carlos", "Jean Carlos R.")).toBe(0.8);
    // Jean Carlos R. (local) matches Jean Carlos (Notion) -> 0.8
    expect(similarity("Jean Carlos R.", "Jean Carlos")).toBe(0.8);
    // Jean (local) vs Jean Carlos R. (Notion) -> no boost (diff > 1)
    expect(similarity("Jean", "Jean Carlos R.")).toBeLessThan(0.4);
  });

  it("should return 0.0 for any word mismatch (regression)", () => {
    // Mismatch in common words -> 0.0
    expect(similarity("Jean Carlos", "Jean Pedro")).toBe(0.0);
    // Mismatch in first word -> 0.0
    expect(similarity("Carlos", "Jean Carlos")).toBe(0.0);
  });

  it("should handle empty strings", () => {
    expect(similarity("", "")).toBe(1.0);
    expect(similarity("John", "")).toBe(0.0);
    expect(similarity("", "John")).toBe(0.0);
  });
});

describe("calculateProjectedTables", () => {
  it("should calculate 1 table for 7-13 tickets", () => {
    expect(calculateProjectedTables(7)).toBe(1);
    expect(calculateProjectedTables(13)).toBe(1);
  });

  it("should calculate 2 tables for 14 tickets", () => {
    expect(calculateProjectedTables(14)).toBe(2);
  });

  it("should return 0 for less than 7 tickets", () => {
    expect(calculateProjectedTables(6)).toBe(0);
    expect(calculateProjectedTables(0)).toBe(0);
  });
});

describe("checkGMShortage", () => {
  it("should return false when assigned >= required", () => {
    expect(checkGMShortage(1, 1)).toBe(false);
    expect(checkGMShortage(2, 1)).toBe(false);
  });

  it("should return true when assigned < required", () => {
    expect(checkGMShortage(0, 1)).toBe(true);
    expect(checkGMShortage(1, 2)).toBe(true);
  });
});

describe("validateOrganizar", () => {
  it("should return null for clean roster", () => {
    const players = [
      { nombre: "P1", partidas_deseadas: 1, partidas_gm: 1, prioridad: 0 },
      { nombre: "P2", partidas_deseadas: 2, partidas_gm: 1, prioridad: 0 },
      { nombre: "P3", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P4", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P5", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P6", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P7", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
    ];
    // totalTickets: 8, projectedTables: 1, assignedGMs: 2
    expect(validateOrganizar(players)).toBeNull();
  });

  it("should detect all ones warning", () => {
    const players = [
      { nombre: "P1", partidas_deseadas: 1, partidas_gm: 1, prioridad: 0 },
      { nombre: "P2", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P3", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P4", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P5", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P6", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P7", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
    ];
    const result = validateOrganizar(players);
    expect(result?.isAllOnes).toBe(true);
  });

  it("should detect GM shortage", () => {
    const players = [
      { nombre: "P1", partidas_deseadas: 2, partidas_gm: 0, prioridad: 0 },
      { nombre: "P2", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P3", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P4", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P5", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P6", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P7", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
    ];
    // totalTickets: 8, projectedTables: 1, assignedGMs: 0
    const result = validateOrganizar(players);
    expect(result?.gmShortage).toEqual({ required: 1, assigned: 0 });
  });

  it("should detect excluded players", () => {
    const players = [
      { nombre: "P1", partidas_deseadas: 2, partidas_gm: 1, prioridad: 0 },
      { nombre: "P2", partidas_deseadas: 0, partidas_gm: 0, prioridad: 0 },
      { nombre: "P3", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P4", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P5", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P6", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
      { nombre: "P7", partidas_deseadas: 1, partidas_gm: 0, prioridad: 0 },
    ];
    const result = validateOrganizar(players);
    expect(result?.excludedPlayers).toContain("P2");
  });
});

describe("detectSimilarNames", () => {
  it("should detect similar names above threshold", () => {
    const notionPlayers = [
      { nombre: "Ren Alegre", experiencia: "Antiguo", juegos_este_ano: 0 },
      { nombre: "P. Knight", experiencia: "Nuevo", juegos_este_ano: 0 },
      { nombre: "John Doe", experiencia: "Antiguo", juegos_este_ano: 0 },
    ];
    const snapshotNames = ["Renato Alegre", "Paul Knight", "Jane Smith"];

    const result = detectSimilarNames(notionPlayers, snapshotNames, 0.75);

    expect(result).toHaveLength(2);
    expect(result[0]?.notion).toBe("Ren Alegre");
    expect(result[0]?.snapshot).toBe("Renato Alegre");
    expect(result[0]?.similarity).toBe(1.0);
    expect(result[1]?.notion).toBe("P. Knight");
    expect(result[1]?.snapshot).toBe("Paul Knight");
    expect(result[1]?.similarity).toBe(1.0);
  });

  it("should skip exact matches", () => {
    const notionPlayers = [
      { nombre: "John Doe", experiencia: "Antiguo", juegos_este_ano: 0 },
      { nombre: "Jane Smith", experiencia: "Antiguo", juegos_este_ano: 0 },
    ];
    const snapshotNames = ["John Doe", "Jane Smith"];

    const result = detectSimilarNames(notionPlayers, snapshotNames, 0.75);

    expect(result).toHaveLength(0);
  });

  it("should sort by similarity descending", () => {
    const notionPlayers = [
      { nombre: "Ren Alegre", experiencia: "Antiguo", juegos_este_ano: 0 },
      { nombre: "P. Knight", experiencia: "Nuevo", juegos_este_ano: 0 },
      { nombre: "Miguel P.", experiencia: "Antiguo", juegos_este_ano: 0 },
    ];
    const snapshotNames = ["Renato Alegre", "Paul Knight", "Miguel Paucar"];

    const result = detectSimilarNames(notionPlayers, snapshotNames, 0.75);

    expect(result).toHaveLength(3);
    // All should have similarity 1.0, but order should be preserved
    expect(result[0]?.similarity).toBe(1.0);
    expect(result[1]?.similarity).toBe(1.0);
    expect(result[2]?.similarity).toBe(1.0);
  });

  it("should respect threshold parameter", () => {
    const notionPlayers = [
      { nombre: "Ren Alegre", experiencia: "Antiguo", juegos_este_ano: 0 },
    ];
    const snapshotNames = ["Renato Alegre"];

    const resultHigh = detectSimilarNames(notionPlayers, snapshotNames, 0.9);
    const resultLow = detectSimilarNames(notionPlayers, snapshotNames, 0.5);

    expect(resultHigh).toHaveLength(1);
    expect(resultLow).toHaveLength(1);
  });

  it("should handle empty arrays", () => {
    expect(detectSimilarNames([], ["John Doe"], 0.75)).toHaveLength(0);
    expect(
      detectSimilarNames(
        [{ nombre: "John Doe", experiencia: "Nuevo", juegos_este_ano: 0 }],
        [],
        0.75,
      ),
    ).toHaveLength(0);
    expect(detectSimilarNames([], [], 0.75)).toHaveLength(0);
  });

  it("should round similarity to 3 decimal places", () => {
    const notionPlayers = [
      { nombre: "Test Name", experiencia: "Nuevo", juegos_este_ano: 0 },
    ];
    const snapshotNames = ["Test Name"];

    const result = detectSimilarNames(notionPlayers, snapshotNames, 0.75);

    // Exact match should be skipped
    expect(result).toHaveLength(0);
  });

  it("should detect similarity against aliases", () => {
    const notionPlayers = [
      {
        nombre: "Renato Alegre",
        experiencia: "Antiguo",
        juegos_este_ano: 0,
        alias: ["ren"],
      },
    ];
    const snapshotNames = ["re"]; // Prefix of "ren"

    const result = detectSimilarNames(notionPlayers, snapshotNames, 0.5);

    expect(result).toHaveLength(1);
    expect(result[0]?.notion).toBe("Renato Alegre");
    expect(result[0]?.snapshot).toBe("re");
    expect(result[0]?.similarity).toBe(1.0);
  });

  it("should skip exact matches against aliases", () => {
    const notionPlayers = [
      {
        nombre: "Renato Alegre",
        experiencia: "Antiguo",
        juegos_este_ano: 0,
        alias: ["ren"],
      },
    ];
    const snapshotNames = ["ren"]; // Exact match with alias

    const result = detectSimilarNames(notionPlayers, snapshotNames, 0.75);

    expect(result).toHaveLength(0);
  });
});
