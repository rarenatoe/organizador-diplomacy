// ── API Utility Module ────────────────────────────────────────────────────────
// Centralized fetch calls for the Diplomacy viewer backend.

import type {
  GameDetail,
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

    // Handle FastAPI HTTPException
    if (typeof data.detail === "string") {
      return { error: data.detail } as T;
    } else if (data.detail && typeof data.detail === "object") {
      // Forward the detail object so the caller can inspect it for collisions
      return { error: "Conflict", detail: data.detail } as unknown as T;
    }

    // Fallback for other errors
    return { error: data.error || "Error de servidor" } as T;
  }

  return data as T;
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

export async function deleteGame(id: number): Promise<void> {
  const res = await fetch(`/api/game/${id}`, { method: "DELETE" });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText);
  }
}
