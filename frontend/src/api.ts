// ── API Utility Module ────────────────────────────────────────────────────────
// Centralized fetch calls for the Diplomacy viewer backend.

import type {
  ChainData,
  SnapshotDetail,
  GameDetail,
  DeleteResult,
  EditPlayerRow,
  SnapshotSaveResponse,
  NotionFetchResponse,
  DraftResponse,
  SaveDraftResponse,
  SaveDraftRequest,
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
): Promise<SnapshotSaveResponse> {
  const res = await fetch("/api/snapshot/new", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ players }),
  });
  return (await res.json()) as SnapshotSaveResponse;
}

export async function saveSnapshot(payload: {
  parent_id: number | null;
  event_type: string;
  players: EditPlayerRow[];
}): Promise<SnapshotSaveResponse> {
  const res = await fetch("/api/snapshot/save", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return (await res.json()) as SnapshotSaveResponse;
}

export async function fetchNotionPlayers(
  snapshotNames: string[] = [],
): Promise<NotionFetchResponse> {
  const res = await fetch("/api/notion/fetch", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot_names: snapshotNames }),
  });
  return (await res.json()) as NotionFetchResponse;
}

// ── Game ──────────────────────────────────────────────────────────────────────

export async function fetchGame(id: number): Promise<GameDetail> {
  const res = await fetch(`/api/game/${id}`);
  return (await res.json()) as GameDetail;
}

export async function fetchGameDraft(
  snapshotId: number,
): Promise<DraftResponse> {
  const res = await fetch("/api/game/draft", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot_id: snapshotId }),
  });
  return (await res.json()) as DraftResponse;
}

export async function saveGameDraft(
  request: SaveDraftRequest,
): Promise<SaveDraftResponse> {
  const res = await fetch("/api/game/save", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return (await res.json()) as SaveDraftResponse;
}

// ── Player ────────────────────────────────────────────────────────────────────

export async function renamePlayer(
  oldName: string,
  newName: string,
): Promise<{ error?: string }> {
  const res = await fetch("/api/player/rename", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_name: oldName, new_name: newName }),
  });
  return (await res.json()) as { error?: string };
}
