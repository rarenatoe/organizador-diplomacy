// ── Sync Utilities Tests ──────────────────────────────────────────────────────

import { describe, it, expect } from "vitest";
import {
  calculateProjectedTables,
  checkGMShortage,
  validateOrganizar,
} from "./syncUtils";
import { normalizeName } from "./utils";

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
