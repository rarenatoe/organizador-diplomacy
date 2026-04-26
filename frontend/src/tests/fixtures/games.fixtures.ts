import type {
  GameDetailResponse,
  GameDraftPlayer,
  GameDraftResponseOutput,
  GameDraftTableOutput,
} from "../../generated-api";

export const createMockDraftPlayer = (
  overrides: Partial<GameDraftPlayer> = {},
): GameDraftPlayer => {
  const baseDraftPlayer: GameDraftPlayer = {
    nombre: "Test Player",
    is_new: false,
    juegos_este_ano: 0,
    has_priority: false,
    partidas_deseadas: 1,
    partidas_gm: 0,
    c_england: 0,
    c_france: 0,
    c_germany: 0,
    c_italy: 0,
    c_austria: 0,
    c_russia: 0,
    c_turkey: 0,
    country: { name: "", reason: [] },
    cupos_faltantes: 0,
  };

  return { ...baseDraftPlayer, ...overrides };
};

export const createMockDraftMesa = (
  overrides: Partial<GameDraftTableOutput> = {},
): GameDraftTableOutput => {
  const baseDraftMesa: GameDraftTableOutput = {
    numero: 1,
    gm: null,
    jugadores: [],
  };

  return { ...baseDraftMesa, ...overrides };
};

export const createMockDraftResponse = (
  overrides: Partial<GameDraftResponseOutput> = {},
): GameDraftResponseOutput => {
  const baseDraftResponse: GameDraftResponseOutput = {
    mesas: [],
    tickets_sobrantes: [],
    minimo_teorico: 0,
    intentos_usados: 0,
  };

  return { ...baseDraftResponse, ...overrides };
};

export const createMockGameDetail = (
  overrides: Partial<GameDetailResponse> = {},
): GameDetailResponse => {
  const baseGameDetail: GameDetailResponse = {
    id: 1,
    created_at: "2024-01-01T00:00:00Z",
    intentos: 1,
    mesas: [],
    waiting_list: [],
    input_snapshot_id: 1,
    output_snapshot_id: 2,
  };

  return { ...baseGameDetail, ...overrides };
};
