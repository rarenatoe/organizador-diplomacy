import type { EditPlayerRow } from "../../types";

export const createMockEditPlayerRow = (
  overrides: Partial<EditPlayerRow> = {},
): EditPlayerRow => {
  const baseEditPlayerRow: EditPlayerRow = {
    nombre: "Test Player",
    notion_id: null,
    notion_name: null,
    is_new: true,
    juegos_este_ano: 0,
    has_priority: false,
    partidas_deseadas: 1,
    partidas_gm: 0,
  };

  return { ...baseEditPlayerRow, ...overrides };
};
