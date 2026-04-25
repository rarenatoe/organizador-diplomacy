// ── Domain types ──────────────────────────────────────────────────────────────

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
