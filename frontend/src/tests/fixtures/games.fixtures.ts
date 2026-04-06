import type {
  DraftPlayer,
  DraftMesa,
  DraftResponse,
  GameDetail,
} from "../../types";

export const createMockDraftPlayer = (
  overrides: Partial<DraftPlayer> = {},
): DraftPlayer => {
  const baseDraftPlayer: DraftPlayer = {
    nombre: "Test Player",
    es_nuevo: false,
    juegos_ano: 0,
    tiene_prioridad: false,
    partidas_deseadas: 1,
    partidas_gm: 0,
    c_england: 0,
    c_france: 0,
    c_germany: 0,
    c_italy: 0,
    c_austria: 0,
    c_russia: 0,
    c_turkey: 0,
    pais: "",
  };

  return { ...baseDraftPlayer, ...overrides };
};

export const createMockDraftMesa = (
  overrides: Partial<DraftMesa> = {},
): DraftMesa => {
  const baseDraftMesa: DraftMesa = {
    numero: 1,
    jugadores: [],
    gm: null,
  };

  return { ...baseDraftMesa, ...overrides };
};

export const createMockDraftResponse = (
  overrides: Partial<DraftResponse> = {},
): DraftResponse => {
  const baseDraftResponse: DraftResponse = {
    mesas: [],
    tickets_sobrantes: [],
    minimo_teorico: 1,
    intentos_usados: 0,
  };

  return { ...baseDraftResponse, ...overrides };
};

export const createMockGameDetail = (
  overrides: Partial<GameDetail> = {},
): GameDetail => {
  const baseGameDetail: GameDetail = {
    id: 1,
    created_at: "2024-01-01T00:00:00Z",
    intentos: 3,
    input_snapshot_id: 10,
    output_snapshot_id: 20,
    mesas: [],
    waiting_list: [],
  };

  return { ...baseGameDetail, ...overrides };
};
