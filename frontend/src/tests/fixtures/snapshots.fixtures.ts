import type { SnapshotDetail } from "../../types";

export const createMockSnapshotDetail = (
  overrides: Partial<SnapshotDetail> = {},
): SnapshotDetail => {
  const baseSnapshotDetail: SnapshotDetail = {
    id: 1,
    created_at: "2024-01-01T00:00:00Z",
    source: "test",
    players: [],
    history: [],
  };

  return { ...baseSnapshotDetail, ...overrides };
};
