// ── Sync Utilities ────────────────────────────────────────────────────────────
// Name similarity detection logic ported from backend/sync/notion_sync.py

import type { SimilarName } from "./types";

// ── Name normalization ────────────────────────────────────────────────────────

/**
 * Normalize a name for comparison: lowercase, strip, collapse whitespace.
 */
export function normalizeName(name: string): string {
  return name.toLowerCase().trim().replace(/\s+/g, " ");
}

// ── Word matching ─────────────────────────────────────────────────────────────

/**
 * Check if two words match, considering abbreviations and prefixes.
 *
 * Rules:
 * - Exact match (case-insensitive)
 * - One is a prefix of the other (e.g., "Ren" matches "Renato", "D" matches "Doe")
 * - One is abbreviated (ends with ".") and matches the start of the other
 *   (e.g., "P." matches "Paul", "D." matches "Doe")
 */
export function wordsMatch(wordA: string, wordB: string): boolean {
  if (!wordA || !wordB) {
    return false;
  }

  const wordALower = wordA.toLowerCase().replace(/\.$/, "");
  const wordBLower = wordB.toLowerCase().replace(/\.$/, "");

  // Exact match (after removing periods)
  if (wordALower === wordBLower) {
    return true;
  }

  // Check if one is a prefix of the other (at least 1 char)
  if (wordALower.length >= 1 && wordBLower.length >= 1) {
    if (
      wordBLower.startsWith(wordALower) ||
      wordALower.startsWith(wordBLower)
    ) {
      return true;
    }
  }

  return false;
}

// ── Similarity calculation ────────────────────────────────────────────────────

/**
 * Calculate similarity ratio between two names (0.0 to 1.0).
 *
 * Uses word-by-word comparison with special handling for abbreviations and prefixes.
 *
 * The algorithm:
 * 1. Splits names into words
 * 2. Compares each word position separately
 * 3. Returns 1.0 if all words match (considering abbreviations/prefixes)
 * 4. Returns 0.0 if any word doesn't match
 *
 * Examples:
 * - "Ren Alegre" vs "Renato Alegre" -> 1.0 (first name is prefix, last name exact)
 * - "Chachi Faker" vs "Charlie Faker" -> 0.0 (first names don't match)
 * - "P. Knight" vs "Paul Knight" -> 1.0 (abbreviated first name matches)
 * - "Miguel P." vs "Miguel Paucar" -> 1.0 (abbreviated last name matches)
 * - "T. Lopez" vs "Tomas L" -> 1.0 (both abbreviated, both match)
 * - "Lori Sanchez" vs "Lori Sal." -> 0.0 (last names don't match)
 * - "Gonzalo Ch." vs "Gonzalo L." -> 0.0 (last names don't match)
 */
export function similarity(a: string, b: string): number {
  const normA = normalizeName(a);
  const normB = normalizeName(b);

  // Handle empty strings
  if (!normA && !normB) {
    return 1.0;
  }
  if (!normA || !normB) {
    return 0.0;
  }

  const wordsA = normA.split(" ");
  const wordsB = normB.split(" ");

  // Must have same number of words
  if (wordsA.length !== wordsB.length) {
    return 0.0;
  }

  // Check each word position
  for (let i = 0; i < wordsA.length; i++) {
    const wordA = wordsA[i];
    const wordB = wordsB[i];
    if (!wordA || !wordB || !wordsMatch(wordA, wordB)) {
      return 0.0;
    }
  }

  // All words match
  return 1.0;
}

// ── Similar name detection ────────────────────────────────────────────────────

/**
 * Detect similar names between Notion and snapshot.
 * Returns list of potential matches: [{"notion": name1, "snapshot": name2, "similarity": 0.85}]
 * Only includes pairs where similarity >= threshold and names are not identical.
 */
export function detectSimilarNames(
  notionNames: string[],
  snapshotNames: string[],
  threshold: number = 0.75,
): SimilarName[] {
  const matches: SimilarName[] = [];

  for (const notionName of notionNames) {
    for (const snapshotName of snapshotNames) {
      // Skip exact matches
      if (normalizeName(notionName) === normalizeName(snapshotName)) {
        continue;
      }

      const sim = similarity(notionName, snapshotName);
      if (sim >= threshold) {
        matches.push({
          notion: notionName,
          snapshot: snapshotName,
          similarity: Math.round(sim * 1000) / 1000, // Round to 3 decimal places
        });
      }
    }
  }

  // Sort by similarity descending
  matches.sort((a, b) => b.similarity - a.similarity);
  return matches;
}
