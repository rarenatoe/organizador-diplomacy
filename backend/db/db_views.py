"""
db_views.py – Read-only query helpers for viewer.py.

Executes complex JOINs to build structured dicts for the REST API.
All write operations live in db.py; this module only reads.

Public API
──────────
  build_chain_data(conn)                     → dict
  get_snapshot_detail(conn, snapshot_id)     → dict | None
  get_game_event_detail(conn, game_event_id) → dict | None
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

from ..organizador.formatter import translate_country
from .db import get_snapshot_players

# ── Chain (viewer) ─────────────────────────────────────────────────────────────

def build_chain_data(conn: sqlite3.Connection) -> dict[str, Any]:
    """
    Builds the full chain tree for /api/chain.

    Returns {"roots": [snapshot_node, …]}

    snapshot_node: {type, id, created_at, source, player_count, is_latest,
                    branches: [{edge, output}, …]}

    edge (sync):  {type:"sync", id, created_at, from_id, to_id}
    edge (game):  {type:"game", id, created_at, from_id, to_id,
                   intentos, mesa_count, espera_count}
    edge (edit):  {type:"edit", id, created_at, from_id, to_id}
    """
    # ── All snapshots ──────────────────────────────────────────────────────────
    snap_rows = {
        int(r["id"]): dict(r)
        for r in conn.execute(
            """
            SELECT s.id, s.created_at, s.source, COUNT(sp.player_id) AS player_count
            FROM   snapshots        s
            LEFT JOIN snapshot_players sp ON sp.snapshot_id = s.id
            GROUP  BY s.id
            ORDER  BY s.id
            """
        ).fetchall()
    }
    if not snap_rows:
        return {"roots": []}

    latest_id = max(snap_rows)

    # ── All edges from unified events table ────────────────────────────────────
    edges: list[dict[str, Any]] = []
    for r in conn.execute(
        """
        SELECT e.id, e.created_at, e.type, e.source_snapshot_id, e.output_snapshot_id,
               gd.intentos,
               COUNT(DISTINCT m.id)  AS mesa_count,
               (SELECT COUNT(*) FROM waiting_list wl WHERE wl.event_id = e.id)
                                     AS espera_count
        FROM   events e
        LEFT JOIN game_details gd ON gd.event_id = e.id
        LEFT JOIN mesas m ON m.event_id = e.id
        WHERE  e.source_snapshot_id IS NOT NULL
        GROUP  BY e.id
        """
    ).fetchall():
        edge: dict[str, Any] = {
            "type": r["type"],
            "id": int(r["id"]),
            "created_at": r["created_at"],
            "from_id": int(r["source_snapshot_id"]),
            "to_id": int(r["output_snapshot_id"]),
        }
        if r["type"] == "game":
            edge["intentos"] = int(r["intentos"])
            edge["mesa_count"] = int(r["mesa_count"])
            edge["espera_count"] = int(r["espera_count"])
        edges.append(edge)

    # ── from_id → [edges] sorted chronologically ──────────────────────────────
    from_to: dict[int, list[dict[str, Any]]] = {}
    for edge in edges:
        from_to.setdefault(edge["from_id"], []).append(edge)
    for lst in from_to.values():
        lst.sort(key=lambda e: e["created_at"])

    # ── Root snapshots ─────────────────────────────────────────────────────────
    # A snapshot is a root if no edge with a non-null source points to it.
    produced_ids: set[int] = {e["to_id"] for e in edges}
    root_ids = [sid for sid in sorted(snap_rows) if sid not in produced_ids]

    visited: set[int] = set()

    def _snap_node(sid: int) -> dict[str, Any]:
        r = snap_rows[sid]
        return {
            "type":         "snapshot",
            "id":           sid,
            "created_at":   r["created_at"],
            "source":       r["source"],
            "player_count": r["player_count"],
            "is_latest":    sid == latest_id,
            "branches":     [],
        }

    def _walk(sid: int) -> dict[str, Any] | None:
        if sid not in snap_rows or sid in visited:
            return None
        visited.add(sid)
        node = _snap_node(sid)
        for edge in from_to.get(sid, []):
            output = _walk(edge["to_id"]) if edge.get("to_id") else None
            node["branches"].append({"edge": edge, "output": output})
        return node

    roots: list[dict[str, Any]] = []
    for r in root_ids:
        n = _walk(r)
        if n is not None:
            roots.append(n)

    # Safety net: snapshots unreachable from any root become additional roots.
    for sid in sorted(snap_rows):
        if sid not in visited:
            n = _walk(sid)
            if n is not None:
                roots.append(n)

    return {"roots": roots}


# ── Viewer detail helpers ──────────────────────────────────────────────────────

def get_snapshot_detail(conn: sqlite3.Connection, snapshot_id: int) -> dict[str, Any] | None:
    """Returns snapshot metadata + player list for the detail panel. None if not found."""
    snap = conn.execute(
        "SELECT id, created_at, source FROM snapshots WHERE id = ?",
        (snapshot_id,),
    ).fetchone()
    if not snap:
        return None
    return {
        "id":         int(snap["id"]),
        "created_at": snap["created_at"],
        "source":     snap["source"],
        "players":    get_snapshot_players(conn, snapshot_id),
    }


def get_game_event_detail(conn: sqlite3.Connection, event_id: int) -> dict[str, Any] | None:
    """Returns full game event detail for the detail panel. None if not found."""
    ge = conn.execute(
        """
        SELECT e.id, e.created_at, e.source_snapshot_id, e.output_snapshot_id,
               gd.intentos, gd.copypaste_text
        FROM   events e
        JOIN   game_details gd ON gd.event_id = e.id
        WHERE  e.id = ? AND e.type = 'game'
        """,
        (event_id,),
    ).fetchone()
    if not ge:
        return None

    input_sid = int(ge["source_snapshot_id"])

    mesas_data: list[dict[str, Any]] = []
    for mesa_row in conn.execute(
        "SELECT id, numero, gm_player_id FROM mesas WHERE event_id = ? ORDER BY numero",
        (event_id,),
    ).fetchall():
        mesa_id = int(mesa_row["id"])

        gm_name: str | None = None
        if mesa_row["gm_player_id"] is not None:
            gm_row = conn.execute(
                "SELECT nombre FROM players WHERE id = ?",
                (mesa_row["gm_player_id"],),
            ).fetchone()
            gm_name = gm_row["nombre"] if gm_row else None

        jugadores: list[dict[str, Any]] = []
        for p in conn.execute(
            """
            SELECT p.nombre, sp.experiencia, sp.juegos_este_ano, mp.pais
            FROM   mesa_players mp
            JOIN   players      p  ON p.id  = mp.player_id
            JOIN   snapshot_players sp
                   ON sp.player_id   = mp.player_id
                   AND sp.snapshot_id = ?
            WHERE  mp.mesa_id = ?
            ORDER  BY mp.orden
            """,
            (input_sid, mesa_id),
        ).fetchall():
            etiqueta = (
                "Nuevo"
                if p["experiencia"] == "Nuevo"
                else f"Antiguo ({p['juegos_este_ano']} juegos)"
            )
            jugadores.append({"nombre": p["nombre"], "etiqueta": etiqueta, "pais": translate_country(p["pais"])})

        mesas_data.append({
            "numero":    int(mesa_row["numero"]),
            "gm":        gm_name,
            "jugadores": jugadores,
        })

    waiting: list[dict[str, Any]] = [
        {
            "nombre": row["nombre"],
            "cupos":  f"{row['cupos_faltantes']} cupo(s) sin asignar",
        }
        for row in conn.execute(
            """
            SELECT p.nombre, wl.cupos_faltantes
            FROM   waiting_list wl
            JOIN   players      p ON p.id = wl.player_id
            WHERE  wl.event_id = ?
            ORDER  BY wl.orden
            """,
            (event_id,),
        ).fetchall()
    ]

    return {
        "id":                 int(ge["id"]),
        "created_at":         ge["created_at"],
        "intentos":           int(ge["intentos"]),
        "copypaste":          ge["copypaste_text"],
        "mesas":              mesas_data,
        "waiting_list":       waiting,
        "input_snapshot_id":  input_sid,
        "output_snapshot_id": int(ge["output_snapshot_id"]),
    }
