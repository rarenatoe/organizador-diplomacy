import type { SnapshotNode, Branch } from "./types";

/**
 * Generic DFS walker for the snapshot chain tree.
 * Calls the callback for each node visited.
 */
export function walkChain(
  roots: SnapshotNode[] | undefined,
  callback: (node: SnapshotNode, branch?: Branch) => void,
): void {
  function visit(node: SnapshotNode): void {
    callback(node);
    for (const branch of node.branches ?? []) {
      callback(node, branch);
      if (branch.output) visit(branch.output);
    }
  }

  if (roots) {
    for (const root of roots) visit(root);
  }
}

/**
 * Finds the latest snapshot ID by checking the is_latest flag
 */
export function findLatestSnapshotId(
  roots: SnapshotNode[] | undefined,
): number | null {
  let latestId: number | null = null;

  walkChain(roots, (node) => {
    if (node.is_latest) {
      latestId = node.id;
    }
  });

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

  walkChain(roots, (_node, branch) => {
    if (branch?.edge.type === "game") {
      const time = new Date(branch.edge.created_at).getTime();
      if (time > latestTime) {
        latestTime = time;
        latestId = branch.edge.id;
      }
    }
  });

  return latestId;
}
