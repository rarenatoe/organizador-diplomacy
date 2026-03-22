// ── Domain types ──────────────────────────────────────────────────────────────

export interface PlayerData {
  nombre: string;
  etiqueta: string;
}

export interface MesaData {
  numero: number;
  gm: string | null;
  jugadores: PlayerData[];
}

export interface WaitingItem {
  nombre: string;
  cupos: string;
}

export interface SnapshotNode {
  type: "snapshot";
  id: number;
  created_at: string;
  source: string;
  player_count: number;
  is_latest: boolean;
  branches?: Branch[];
}

export interface GameEdge {
  type: "game";
  id: number;
  created_at: string;
  from_id: number;
  to_id: number;
  intentos: number;
  mesa_count: number;
  espera_count: number;
}

export interface SyncEdge {
  type: "sync";
  id: number;
  created_at: string;
  from_id: number;
  to_id: number;
}

export type EdgeNode = GameEdge | SyncEdge;

export interface Branch {
  edge: EdgeNode;
  output: SnapshotNode | null;
}

export interface ChainData {
  roots?: SnapshotNode[];
}

export interface RunResult {
  returncode: number;
  stdout?: string;
  stderr?: string;
}

export interface SnapshotDetail {
  id: number;
  created_at: string;
  source: string;
  players?: Record<string, string | number>[];
}

export interface GameDetail {
  id: number;
  created_at: string;
  intentos: number;
  copypaste: string;
  mesas?: MesaData[];
  waiting_list?: WaitingItem[];
  input_snapshot_id: number;
  output_snapshot_id: number;
}

export interface DeleteResult {
  deleted: number[];
  error?: string;
}

export interface EditPlayerRow {
  nombre: string;
  prioridad: number;
  partidas_deseadas: number;
  partidas_gm: number;
}

export interface EditSnapshotResponse {
  snapshot_id?: number;
  error?: string;
}
