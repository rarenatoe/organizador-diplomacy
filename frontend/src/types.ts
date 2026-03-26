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

export interface EditEdge {
  type: "edit";
  id: number;
  created_at: string;
  from_id: number;
  to_id: number;
}

export type EdgeNode = GameEdge | SyncEdge | EditEdge;

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
  players?: EditPlayerRow[];
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
  experiencia?: string;
  juegos_este_ano?: number;
  prioridad: number;
  partidas_deseadas: number;
  partidas_gm: number;
}

export interface SnapshotSaveResponse {
  snapshot_id: number;
  error?: string;
}

export interface NotionFetchResponse {
  players: NotionPlayer[];
  error?: string;
}

export interface NotionPlayer {
  nombre: string;
  experiencia: string;
  juegos_este_ano: number;
  alias?: string[];
}

export interface SimilarName {
  notion: string;
  snapshot: string;
  similarity: number;
}

export interface OrganizarValidation {
  isAllOnes: boolean;
  gmShortage: {
    required: number;
    assigned: number;
  } | null;
  excludedPlayers: string[];
}

export interface SyncDetectResult {
  notion_count: number;
  snapshot_count: number;
  similar_names: SimilarName[];
  error?: string;
}

export interface MergePair {
  from: string;
  to: string;
  action: ResolutionAction;
}

// ── Toast notification types ─────────────────────────────────────────────────

export type ToastState = "syncing" | "success" | "error";

export interface ToastOptions {
  state: ToastState;
  message: string;
  dismissible?: boolean;
}

// ── Resolution card types ────────────────────────────────────────────────────

export type ResolutionAction = "merge_notion" | "merge_local" | "skip";

export interface ResolutionDecision {
  pair: SimilarName;
  action: ResolutionAction;
}

export interface ResolutionState {
  pairs: SimilarName[];
  currentIndex: number;
  decisions: ResolutionDecision[];
  snapshotId: number | null;
}

// ── Snapshot Group types (UI transformation) ─────────────────────────────────

export interface SnapshotVersion {
  snapshot: SnapshotNode;
  incomingEdge: SyncEdge | EditEdge | null; // The event that created THIS version (null for the root of the group)
}

export interface SnapshotGroup {
  versions: SnapshotVersion[];
  branches: Branch[]; // The branches emanating from the LAST version in this group
}
