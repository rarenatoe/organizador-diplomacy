// ── Sync Utilities ────────────────────────────────────────────────────
// Name similarity detection logic ported from backend/sync/notion_sync.py

import { MergePair } from "./syncResolution";
import type { OrganizarValidation } from "./types";
import type { NotionPlayerData } from "./generated-api";
import { normalizeName } from "./utils";

type OrganizarPlayer = {
  nombre: string;
  partidas_deseadas: number;
  partidas_gm: number;
};

type SyncMergePlayer = {
  nombre: string;
  notion_id?: string | null;
  notion_name?: string | null;
  is_new?: boolean;
  juegos_este_ano?: number;
};

// ── Validation Utilities ──────────────────────────────────────────────────────

/**
 * Calculate how many tables are expected based on the total number of tickets.
 * Each table requires exactly 7 players.
 */
export function calculateProjectedTables(totalTickets: number): number {
  return Math.floor(totalTickets / 7);
}

/**
 * Check if there is a shortage of GMs for the projected number of tables.
 */
export function checkGMShortage(assigned: number, required: number): boolean {
  return assigned < required;
}

/**
 * Perform pre-flight validation for organizing games.
 * Returns a validation object if warnings are found, null otherwise.
 */
export function validateOrganizar(
  players: OrganizarPlayer[],
): OrganizarValidation | null {
  if (players.length === 0) return null;

  const totalTickets = players.reduce((sum, p) => sum + p.partidas_deseadas, 0);
  const projectedTables = calculateProjectedTables(totalTickets);
  const assignedGMs = players.reduce((sum, p) => sum + p.partidas_gm, 0);
  const isAllOnes = players.every((p) => p.partidas_deseadas === 1);
  const excludedPlayers = players
    .filter((p) => p.partidas_deseadas === 0)
    .map((p) => p.nombre);

  const hasGmShortage = checkGMShortage(assignedGMs, projectedTables);

  if (isAllOnes || excludedPlayers.length > 0 || hasGmShortage) {
    return {
      isAllOnes,
      gmShortage: hasGmShortage
        ? { required: projectedTables, assigned: assignedGMs }
        : null,
      excludedPlayers,
    };
  }

  return null;
}

export function applySyncMerges<T extends SyncMergePlayer>(
  currentRows: T[],
  merges: MergePair[],
  fetchedNotionPlayers: NotionPlayerData[],
): T[] {
  const renameActions = ["link_rename", "merge_notion", "use_existing"];
  const mergeMap = new Map(merges.map((m) => [m.from, m]));
  const seenNames = new Set<string>();
  const deduplicatedPlayers: T[] = [];

  for (const row of currentRows) {
    const mergeInfo = mergeMap.get(row.nombre);

    // The final display name we will save in the database
    const newName =
      mergeInfo && renameActions.includes(mergeInfo.action)
        ? mergeInfo.to
        : row.nombre;

    // The identity we use to look up the Notion record (always use 'to' if a merge exists)
    const searchIdentity = mergeInfo ? mergeInfo.to : row.nombre;
    const normSearch = normalizeName(searchIdentity);

    // Deduplicate based on the final saved name
    const normName = normalizeName(newName);
    if (seenNames.has(normName)) continue;
    seenNames.add(normName);

    // Search Notion players using the search identity, not the local typo
    const notionPlayer = fetchedNotionPlayers.find(
      (p) =>
        (row.notion_id && p.notion_id === row.notion_id) ||
        normalizeName(p.nombre) === normSearch ||
        p.alias?.some((a: string) => normalizeName(a) === normSearch),
    );

    if (notionPlayer) {
      deduplicatedPlayers.push({
        ...row,
        nombre: newName,
        is_new: notionPlayer.is_new,
        juegos_este_ano: notionPlayer.juegos_este_ano,
        notion_id: notionPlayer.notion_id || null,
        notion_name: notionPlayer.nombre || null,
      } as T);
    } else {
      deduplicatedPlayers.push({ ...row, nombre: newName } as T);
    }
  }
  return deduplicatedPlayers;
}
