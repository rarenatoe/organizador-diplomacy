// ── Sync Utilities ────────────────────────────────────────────────────────────
// Name similarity detection logic ported from backend/sync/notion_sync.py

import type { EditPlayerRow, OrganizarValidation } from "./types";

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
  players: EditPlayerRow[],
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
