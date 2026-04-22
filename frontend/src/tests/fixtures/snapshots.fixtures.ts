import type { SnapshotDetailResponse } from "../../generated-api";

export const createMockSnapshotDetail = (
  overrides: Partial<SnapshotDetailResponse> = {},
): SnapshotDetailResponse => {
  const baseSnapshotDetail: SnapshotDetailResponse = {
    id: 1,
    created_at: "2024-01-01T00:00:00Z",
    source: "manual",
    players: [],
    history: [],
  };

  return { ...baseSnapshotDetail, ...overrides };
};
