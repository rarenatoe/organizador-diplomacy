// ── API Utility Module ────────────────────────────────────────────────────────
// Centralized fetch calls for the Diplomacy viewer backend.

import type {
  ChainData,
  SnapshotDetail,
  GameDetail,
  RunResult,
  SyncDetectResult,
  MergePair,
  DeleteResult,
  EditPlayerRow,
  EditSnapshotResponse,
} from "./types";

// ── Chain ─────────────────────────────────────────────────────────────────────

export async function fetchChain(): Promise<ChainData> {
  const res = await fetch("/api/chain");
  return (await res.json()) as ChainData;
}

// ── Snapshot ──────────────────────────────────────────────────────────────────

export async function fetchSnapshot(id: number): Promise<SnapshotDetail> {
  const res = await fetch(`/api/snapshot/${id}`);
  return (await res.json()) as SnapshotDetail;
}

export async function deleteSnapshot(id: number): Promise<DeleteResult> {
  const res = await fetch(`/api/snapshot/${id}`, { method: "DELETE" });
  return (await res.json()) as DeleteResult;
}

export async function createSnapshot(
  players: EditPlayerRow[],
): Promise<EditSnapshotResponse> {
  const res = await fetch("/api/snapshot/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ players }),
  });
  return (await res.json()) as EditSnapshotResponse;
}

export async function editSnapshot(
  id: number,
  players: EditPlayerRow[],
): Promise<EditSnapshotResponse> {
  const res = await fetch(`/api/snapshot/${id}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ players }),
  });
  return (await res.json()) as EditSnapshotResponse;
}

export async function addPlayer(
  snapshotId: number,
  player: {
    nombre: string;
    experiencia: string;
    juegos_este_ano: number;
    prioridad: number;
    partidas_deseadas: number;
    partidas_gm: number;
  },
): Promise<{ error?: string }> {
  const res = await fetch(`/api/snapshot/${snapshotId}/add-player`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(player),
  });
  return (await res.json()) as { error?: string };
}

// ── Game ──────────────────────────────────────────────────────────────────────

export async function fetchGame(id: number): Promise<GameDetail> {
  const res = await fetch(`/api/game/${id}`);
  return (await res.json()) as GameDetail;
}

// ── Player ────────────────────────────────────────────────────────────────────

export async function renamePlayer(
  oldName: string,
  newName: string,
): Promise<{ error?: string }> {
  const res = await fetch("/api/player/rename", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_name: oldName, new_name: newName }),
  });
  return (await res.json()) as { error?: string };
}

// ── Scripts ───────────────────────────────────────────────────────────────────

export async function runScript(
  script: string,
  snapshotId: number | null = null,
): Promise<RunResult> {
  const init: RequestInit = { method: "POST" };
  if (snapshotId !== null) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify({ snapshot: snapshotId });
  }
  const res = await fetch(`/api/run/${script}`, init);
  return (await res.json()) as RunResult;
}

// ── Sync ──────────────────────────────────────────────────────────────────────

export async function detectSync(
  snapshotId: number | null,
): Promise<SyncDetectResult> {
  const res = await fetch("/api/sync/detect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot: snapshotId }),
  });
  return (await res.json()) as SyncDetectResult;
}

export async function confirmSync(
  snapshotId: number | null,
  merges: MergePair[],
): Promise<RunResult> {
  const res = await fetch("/api/sync/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot: snapshotId, merges }),
  });
  return (await res.json()) as RunResult;
}
