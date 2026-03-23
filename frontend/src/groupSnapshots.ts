import type {
  SnapshotNode,
  SnapshotGroup,
  SnapshotVersion,
  Branch,
  SyncEdge,
  EditEdge,
} from "./types";

/**
 * Determines if a snapshot can absorb its child into the same group.
 * A snapshot can absorb its child IF AND ONLY IF:
 * 1. It has exactly one branch.
 * 2. That branch's edge type is `sync` or `edit` (NOT `game`).
 */
function canAbsorbChild(node: SnapshotNode): boolean {
  const branches = node.branches ?? [];
  if (branches.length !== 1) return false;
  const firstBranch = branches[0];
  if (!firstBranch) return false;
  const edgeType = firstBranch.edge.type;
  return edgeType === "sync" || edgeType === "edit";
}

/**
 * Recursively transforms a flat snapshot tree into grouped SnapshotGroups.
 * Linear sequences of sync/edit events are collapsed into paginated groups.
 * @param roots - The root snapshot nodes to group
 * @param initialIncomingEdge - The edge that points to these roots (for child groups)
 */
export function groupSnapshots(
  roots: SnapshotNode[],
  initialIncomingEdge: SyncEdge | EditEdge | null = null,
): SnapshotGroup[] {
  return roots.map((root) => buildGroup(root, initialIncomingEdge));
}

/**
 * Builds a single SnapshotGroup starting from the given node.
 * Absorbs consecutive sync/edit children into the same group.
 */
function buildGroup(
  startNode: SnapshotNode,
  initialIncomingEdge: SyncEdge | EditEdge | null = null,
): SnapshotGroup {
  const versions: SnapshotVersion[] = [];
  let current: SnapshotNode = startNode;

  // The root of the group uses the initialIncomingEdge (if provided)
  versions.push({
    snapshot: current,
    incomingEdge: initialIncomingEdge,
  });

  // Absorb children while the grouping rule allows it
  while (canAbsorbChild(current)) {
    const branches: Branch[] = current.branches ?? [];
    const branch = branches[0] as Branch;
    const edge = branch.edge as SyncEdge | EditEdge;
    const child = branch.output;

    if (!child) break;

    versions.push({
      snapshot: child,
      incomingEdge: edge,
    });

    current = child;
  }

  // The branches that emanate from the LAST version in this group
  const finalBranches: Branch[] = current.branches ?? [];

  return { versions, branches: finalBranches };
}
