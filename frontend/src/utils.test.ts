/**
 * Tests for utils.ts
 */
import { describe, expect, it } from "vitest";

import { parsePlayersCsv } from "./utils";

describe("parsePlayersCsv", () => {
  it("parses CSV with all columns", () => {
    const csv = `nombre,experiencia,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm
Alice,Nuevo,0,0,1,0
Bob,Antiguo,3,1,2,1`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      nombre: "Alice",
      is_new: true,
      juegos_este_ano: 0,
      has_priority: false,
      partidas_deseadas: 1,
      partidas_gm: 0,
    });
    expect(result[1]).toEqual({
      nombre: "Bob",
      is_new: false,
      juegos_este_ano: 3,
      has_priority: true,
      partidas_deseadas: 2,
      partidas_gm: 1,
    });
  });

  it("applies defaults for missing columns", () => {
    const csv = `nombre
Charlie`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      nombre: "Charlie",
      is_new: true,
      juegos_este_ano: 0,
      has_priority: false,
      partidas_deseadas: 1,
      partidas_gm: 0,
    });
  });

  it("skips empty rows", () => {
    const csv = `nombre,experiencia
Alice,Nuevo

Bob,Antiguo
`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(2);
    expect(result[0]?.nombre).toBe("Alice");
    expect(result[1]?.nombre).toBe("Bob");
  });

  it("skips rows without nombre", () => {
    const csv = `nombre,experiencia
Alice,Nuevo
,Antiguo
Bob,Nuevo`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(2);
    expect(result[0]?.nombre).toBe("Alice");
    expect(result[1]?.nombre).toBe("Bob");
  });

  it("returns empty array for empty input", () => {
    const result = parsePlayersCsv("");
    expect(result).toEqual([]);
  });

  it("handles case-insensitive headers", () => {
    const csv = `Nombre,experiencia
Alice,nuevo`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(1);
    expect(result[0]?.nombre).toBe("Alice");
    expect(result[0]?.is_new).toBe(true);
  });

  it("handles columns in different order", () => {
    const csv = `experiencia,nombre,prioridad
Antiguo,Bob,1`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(1);
    expect(result[0]?.nombre).toBe("Bob");
    expect(result[0]?.is_new).toBe(false);
    expect(result[0]?.has_priority).toBe(true);
  });

  it("parses numeric values correctly", () => {
    const csv = `nombre,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm
Alice,5,1,3,2`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(1);
    expect(result[0]?.juegos_este_ano).toBe(5);
    expect(result[0]?.has_priority).toBe(true);
    expect(result[0]?.partidas_deseadas).toBe(3);
    expect(result[0]?.partidas_gm).toBe(2);
  });

  it("handles invalid numeric values with defaults", () => {
    const csv = `nombre,juegos_este_ano,prioridad
Alice,abc,xyz`;
    const result = parsePlayersCsv(csv);
    expect(result).toHaveLength(1);
    expect(result[0]?.juegos_este_ano).toBe(0);
    expect(result[0]?.has_priority).toBe(false);
  });
});
