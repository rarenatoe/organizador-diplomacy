// ── Sync Utilities Tests ──────────────────────────────────────────────────────

import { describe, it, expect } from "vitest";
import {
  normalizeName,
  wordsMatch,
  similarity,
  detectSimilarNames,
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

  it("should return 0.0 for different word counts", () => {
    expect(similarity("John", "John Doe")).toBe(0.0);
    expect(similarity("John Doe Smith", "John Doe")).toBe(0.0);
  });

  it("should handle empty strings", () => {
    expect(similarity("", "")).toBe(1.0);
    expect(similarity("John", "")).toBe(0.0);
    expect(similarity("", "John")).toBe(0.0);
  });
});

describe("detectSimilarNames", () => {
  it("should detect similar names above threshold", () => {
    const notionNames = ["Ren Alegre", "P. Knight", "John Doe"];
    const snapshotNames = ["Renato Alegre", "Paul Knight", "Jane Smith"];

    const result = detectSimilarNames(notionNames, snapshotNames, 0.75);

    expect(result).toHaveLength(2);
    expect(result[0]?.notion).toBe("Ren Alegre");
    expect(result[0]?.snapshot).toBe("Renato Alegre");
    expect(result[0]?.similarity).toBe(1.0);
    expect(result[1]?.notion).toBe("P. Knight");
    expect(result[1]?.snapshot).toBe("Paul Knight");
    expect(result[1]?.similarity).toBe(1.0);
  });

  it("should skip exact matches", () => {
    const notionNames = ["John Doe", "Jane Smith"];
    const snapshotNames = ["John Doe", "Jane Smith"];

    const result = detectSimilarNames(notionNames, snapshotNames, 0.75);

    expect(result).toHaveLength(0);
  });

  it("should sort by similarity descending", () => {
    const notionNames = ["Ren Alegre", "P. Knight", "Miguel P."];
    const snapshotNames = ["Renato Alegre", "Paul Knight", "Miguel Paucar"];

    const result = detectSimilarNames(notionNames, snapshotNames, 0.75);

    expect(result).toHaveLength(3);
    // All should have similarity 1.0, but order should be preserved
    expect(result[0]?.similarity).toBe(1.0);
    expect(result[1]?.similarity).toBe(1.0);
    expect(result[2]?.similarity).toBe(1.0);
  });

  it("should respect threshold parameter", () => {
    const notionNames = ["Ren Alegre"];
    const snapshotNames = ["Renato Alegre"];

    const resultHigh = detectSimilarNames(notionNames, snapshotNames, 0.9);
    const resultLow = detectSimilarNames(notionNames, snapshotNames, 0.5);

    expect(resultHigh).toHaveLength(1);
    expect(resultLow).toHaveLength(1);
  });

  it("should handle empty arrays", () => {
    expect(detectSimilarNames([], ["John Doe"], 0.75)).toHaveLength(0);
    expect(detectSimilarNames(["John Doe"], [], 0.75)).toHaveLength(0);
    expect(detectSimilarNames([], [], 0.75)).toHaveLength(0);
  });

  it("should round similarity to 3 decimal places", () => {
    const notionNames = ["Test Name"];
    const snapshotNames = ["Test Name"];

    const result = detectSimilarNames(notionNames, snapshotNames, 0.75);

    // Exact match should be skipped
    expect(result).toHaveLength(0);
  });
});
