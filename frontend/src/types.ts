// ── Domain types ──────────────────────────────────────────────────────────────
export interface CountryAssignment {
  name: string;
  reason?: string;
}

export interface PlayerData {
  nombre: string;
  notion_id?: string | null;
  notion_name?: string | null;
  notion_alias?: string[] | null;
  country?: CountryAssignment | null;
  is_new?: boolean;
  juegos_este_ano?: number;
  has_priority?: boolean;
  partidas_deseadas?: number;
  partidas_gm?: number;
  c_england?: number;
  c_france?: number;
  c_germany?: number;
  c_italy?: number;
  c_austria?: number;
  c_russia?: number;
  c_turkey?: number;
  cupos?: number;
}

export interface MesaData {
  numero: number;
  gm: string | null;
  jugadores: PlayerData[];
}

export interface WaitingItem {
  nombre: string;
  notion_id?: string | null;
  notion_name?: string | null;
  notion_alias?: string[] | null;
  cupos_faltantes: number;
  country?: CountryAssignment | null;
  is_new?: boolean;
  juegos_este_ano?: number;
  has_priority?: boolean;
  partidas_deseadas?: number;
  partidas_gm?: number;
  c_england?: number;
  c_france?: number;
  c_germany?: number;
  c_italy?: number;
  c_austria?: number;
  c_russia?: number;
  c_turkey?: number;
}

export interface GameDetail {
  id: number;
  created_at: string;
  intentos: number;
  mesas?: MesaData[];
  waiting_list?: WaitingItem[];
  input_snapshot_id: number;
  output_snapshot_id: number;
}

export interface EditPlayerRow {
  nombre: string;
  notion_id?: string | null;
  notion_name?: string | null;
  oldName?: string;
  is_new?: boolean;
  juegos_este_ano?: number;
  has_priority: boolean;
  partidas_deseadas: number;
  partidas_gm: number;
  historyRestored?: boolean;
}

export interface OrganizarValidation {
  isAllOnes: boolean;
  gmShortage: {
    required: number;
    assigned: number;
  } | null;
  excludedPlayers: string[];
}

// ── Toast notification types ─────────────────────────────────────────────────

export type ToastState = "syncing" | "success" | "error";

// ── Draft Mode types ─────────────────────────────────────────────────────────

export interface DraftPlayer {
  nombre: string;
  notion_id?: string | null;
  notion_name?: string | null;
  notion_alias?: string[] | null;
  is_new: boolean;
  juegos_ano: number;
  has_priority: boolean;
  partidas_deseadas: number;
  partidas_gm: number;
  c_england: number;
  c_france: number;
  c_germany: number;
  c_italy: number;
  c_austria: number;
  c_russia: number;
  c_turkey: number;
  country?: CountryAssignment | null;
}

export interface DraftMesa {
  numero: number;
  jugadores: DraftPlayer[];
  gm: DraftPlayer | null;
}

export interface DraftResponse {
  mesas: DraftMesa[];
  tickets_sobrantes: DraftPlayer[];
  minimo_teorico: number;
  intentos_usados: number;
  error?: string;
}

export interface SaveDraftResponse {
  game_id: number;
  error?: string;
}

export interface SaveDraftRequest {
  snapshot_id: number;
  draft: DraftResponse;
  editing_game_id?: number | null;
}
