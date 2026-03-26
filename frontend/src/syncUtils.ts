// ── Sync Utilities ────────────────────────────────────────────────────────────
// Name similarity detection logic ported from backend/sync/notion_sync.py

import type { SimilarName, NotionPlayer } from "./types";

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
 * Handles names with different word counts by comparing common prefix words.
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

  // Compare word by word up to the length of the shorter name
  const minLen = Math.min(wordsA.length, wordsB.length);
  if (minLen === 0) {
    return 0.0;
  }

  let matchedWords = 0;
  for (let i = 0; i < minLen; i++) {
    const wordA = wordsA[i];
    const wordB = wordsB[i];
    if (wordA && wordB && wordsMatch(wordA, wordB)) {
      matchedWords++;
    } else {
      return 0.0; // Any mismatch in prefix words results in 0 similarity
    }
  }

  // Calculate similarity as the ratio of matched words over the longest name length
  const maxLen = Math.max(wordsA.length, wordsB.length);

  // BONUS: If it's a perfect prefix match (all words of shorter name match)
  // and the difference is only 1 word, we boost the similarity to 0.8
  // This helps "Jean Carlos" vs "Jean Carlos R." match at 0.75 threshold.
  if (matchedWords === minLen && maxLen - minLen === 1) {
    return Math.max(0.8, matchedWords / maxLen);
  }

  return matchedWords / maxLen;
}

// ── Similar name detection ────────────────────────────────────────────────────

/**
 * Detect similar names between Notion (including aliases) and snapshot.
 * Returns list of potential matches, sorted by similarity.
 */
export function detectSimilarNames(
  notionPlayers: NotionPlayer[],
  snapshotNames: string[],
  threshold: number = 0.75
): SimilarName[] {
  const matchesMap = new Map<string, SimilarName>(); // key: "notionMainName|snapshotName"

  for (const player of notionPlayers) {
    const notionMainName = player.nombre;
    const allNotionVariations = [notionMainName, ...(player.alias || [])];

    for (const snapshotName of snapshotNames) {
      const normSnapshot = normalizeName(snapshotName);

      // Skip if any variation is an exact match
      const isExactMatch = allNotionVariations.some(
        (v) => normalizeName(v) === normSnapshot
      );
      if (isExactMatch) {
        continue;
      }

      // Check similarity against all variations
      let bestSim = 0;
      for (const variation of allNotionVariations) {
        const sim = similarity(variation, snapshotName);
        if (sim > bestSim) {
          bestSim = sim;
        }
      }

      if (bestSim >= threshold) {
        const key = `${notionMainName}|${snapshotName}`;
        const existing = matchesMap.get(key);
        if (!existing || bestSim > existing.similarity) {
          matchesMap.set(key, {
            notion: notionMainName,
            snapshot: snapshotName,
            similarity: Number(bestSim.toFixed(3)),
          });
        }
      }
    }
  }

  const matches = Array.from(matchesMap.values());
  // Sort by similarity descending
  matches.sort((a, b) => b.similarity - a.similarity);
  return matches;
}
