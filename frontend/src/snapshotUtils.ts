import type { SnapshotNode } from "./types";

/**
 * Finds the latest snapshot ID by checking the is_latest flag
 */
export function findLatestSnapshotId(
  roots: SnapshotNode[] | undefined,
): number | null {
  let latestId: number | null = null;

  function visit(node: SnapshotNode): void {
    if (node.is_latest) {
      latestId = node.id;
    }
    for (const branch of node.branches ?? []) {
      if (branch.output) visit(branch.output);
    }
  }

  if (roots) {
    for (const root of roots) visit(root);
  }
  return latestId;
}

/**
 * Finds the latest game ID by comparing created_at timestamps
 */
export function findLatestGameId(
  roots: SnapshotNode[] | undefined,
): number | null {
  let latestId: number | null = null;
  let latestTime = 0;

  function visit(node: SnapshotNode): void {
    for (const branch of node.branches ?? []) {
      if (branch.edge.type === "game") {
        const time = new Date(branch.edge.created_at).getTime();
        if (time > latestTime) {
          latestTime = time;
          latestId = branch.edge.id;
        }
      }
      if (branch.output) visit(branch.output);
    }
  }

  if (roots) {
    for (const root of roots) visit(root);
  }
  return latestId;
}
