import type { EditPlayerRow } from "../../types";

export const createMockEditPlayerRow = (
  overrides: Partial<EditPlayerRow> = {},
): EditPlayerRow => {
  const baseEditPlayerRow: EditPlayerRow = {
    nombre: "Test Player",
    experiencia: "Nuevo",
    juegos_este_ano: 0,
    prioridad: 0,
    partidas_deseadas: 1,
    partidas_gm: 0,
  };

  return { ...baseEditPlayerRow, ...overrides };
};
