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

// ── Error Handling ────────────────────────────────────────────────────────────

interface FastAPIValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

interface ErrorResponse {
  detail?: FastAPIValidationError[] | string;
  error?: string;
}

function isErrorResponse(data: unknown): data is ErrorResponse {
  return (
    typeof data === "object" &&
    data !== null &&
    ("detail" in data || "error" in data)
  );
}

function isFastAPIValidationError(
  detail: unknown,
): detail is FastAPIValidationError[] {
  return (
    Array.isArray(detail) &&
    detail.length > 0 &&
    typeof detail[0] === "object" &&
    detail[0] !== null &&
    "msg" in detail[0]
  );
}

async function safeFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  const data: unknown = await res.json();

  if (!res.ok) {
    if (!isErrorResponse(data)) {
      return { error: "Error de servidor" } as T;
    }

    // Handle 422 validation errors - extract msg strings from detail array
    if (res.status === 422 && isFastAPIValidationError(data.detail)) {
      const messages = data.detail.map((err) => err.msg);
      return { error: messages.join("; ") } as T;
    }

    // Handle FastAPI HTTPException - normalize "detail" to "error"
    if (typeof data.detail === "string") {
      return { error: data.detail } as T;
    }

    // Fallback for other errors
    return { error: data.error || "Error de servidor" } as T;
  }

  return data as T;
}

// ── Chain ─────────────────────────────────────────────────────────────────────

export async function fetchChain(): Promise<ChainData> {
  return safeFetch<ChainData>("/api/chain");
}

// ── Snapshot ──────────────────────────────────────────────────────────────────

export async function fetchSnapshot(id: number): Promise<SnapshotDetail> {
  return safeFetch<SnapshotDetail>(`/api/snapshot/${id}`);
}

export async function deleteSnapshot(id: number): Promise<DeleteResult> {
  return safeFetch<DeleteResult>(`/api/snapshot/${id}`, { method: "DELETE" });
}

export async function createSnapshot(
  players: EditPlayerRow[],
): Promise<SnapshotSaveResponse> {
  return safeFetch<SnapshotSaveResponse>("/api/snapshot/new", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ players }),
  });
}

export async function saveSnapshot(payload: {
  parent_id: number | null;
  event_type: string;
  players: EditPlayerRow[];
}): Promise<SnapshotSaveResponse> {
  return safeFetch<SnapshotSaveResponse>("/api/snapshot/save", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchNotionPlayers(
  snapshotNames: string[] = [],
): Promise<NotionFetchResponse> {
  return safeFetch<NotionFetchResponse>("/api/notion/fetch", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot_names: snapshotNames }),
  });
}

// ── Game ──────────────────────────────────────────────────────────────────────

export async function fetchGame(id: number): Promise<GameDetail> {
  return safeFetch<GameDetail>(`/api/game/${id}`);
}

export async function fetchGameDraft(
  snapshotId: number,
): Promise<DraftResponse> {
  return safeFetch<DraftResponse>("/api/game/draft", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot_id: snapshotId }),
  });
}

export async function saveGameDraft(
  request: SaveDraftRequest,
): Promise<SaveDraftResponse> {
  return safeFetch<SaveDraftResponse>("/api/game/save", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

// ── Player ────────────────────────────────────────────────────────────────────

export async function renamePlayer(
  oldName: string,
  newName: string,
): Promise<{ error?: string }> {
  return safeFetch<{ error?: string }>("/api/player/rename", {
    method: "POST",
    // eslint-disable-next-line @typescript-eslint/naming-convention -- HTTP header field name
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_name: oldName, new_name: newName }),
  });
}
