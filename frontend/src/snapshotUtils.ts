import type { SnapshotNode, Branch, EditPlayerRow } from "./types";

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

/**
 * Builds a complete EditPlayerRow from base data and history
 */
export function buildPlayerRow(
  base: Partial<EditPlayerRow> & { nombre: string },
  history: Partial<
    EditPlayerRow & { source: "history" | "notion" | "default" }
  >,
): EditPlayerRow {
  return {
    nombre: base.nombre,
    original_nombre: base.nombre,
    is_new: base.is_new ?? history.is_new ?? true,
    juegos_este_ano: base.juegos_este_ano ?? history.juegos_este_ano ?? 0,
    has_priority: base.has_priority ?? history.has_priority ?? false,
    partidas_deseadas: base.partidas_deseadas ?? history.partidas_deseadas ?? 1,
    partidas_gm: base.partidas_gm ?? history.partidas_gm ?? 0,
    notion_id: base.notion_id ?? history.notion_id ?? null,
    notion_name: base.notion_name ?? history.notion_name ?? null,
    historyRestored: history.source === "history",
  };
}
