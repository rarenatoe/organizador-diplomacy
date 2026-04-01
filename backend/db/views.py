"""Async view queries for the REST API.

This module provides async read-only queries for the Diplomacy organizer,
migrating from raw SQLite to SQLAlchemy 2.0 with async sessions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.crud import get_snapshot_players
from backend.db.models import (
    Player,
    Snapshot,
    SnapshotHistory,
)


async def build_chain_data(session: AsyncSession) -> dict[str, Any]:
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
    # Get all snapshots with player counts using text() for complex aggregation
    snap_query = text("""
        SELECT s.id, s.created_at, s.source, COUNT(sp.player_id) AS player_count
        FROM   snapshots        s
        LEFT JOIN snapshot_players sp ON sp.snapshot_id = s.id
        GROUP  BY s.id
        ORDER  BY s.id
    """)
    result = await session.execute(snap_query)
    snap_rows = {
        int(r[0]): {"id": r[0], "created_at": r[1], "source": r[2], "player_count": r[3]}
        for r in result.all()
    }

    if not snap_rows:
        return {"roots": []}

    latest_id = max(snap_rows)

    # Get all edges from unified timeline_edges table
    edges_query = text("""
        SELECT e.id, e.created_at, e.edge_type, e.source_snapshot_id, e.output_snapshot_id,
               gd.attempts,
               COUNT(DISTINCT m.id)  AS mesa_count,
               (SELECT COUNT(*) FROM waiting_list wl WHERE wl.timeline_edge_id = e.id)
                                     AS espera_count
        FROM   timeline_edges e
        LEFT JOIN game_details gd ON gd.timeline_edge_id = e.id
        LEFT JOIN game_tables m ON m.timeline_edge_id = e.id
        WHERE  e.source_snapshot_id IS NOT NULL
        GROUP  BY e.id
    """)
    result = await session.execute(edges_query)

    edges: list[dict[str, Any]] = []
    for r in result.all():
        edge: dict[str, Any] = {
            "type": r[2],
            "id": int(r[0]),
            "created_at": r[1],
            "from_id": int(r[3]),
            "to_id": int(r[4]),
        }
        if r[2] == "game":
            edge["intentos"] = int(r[5] or 0)
            edge["mesa_count"] = int(r[6])
            edge["espera_count"] = int(r[7])
        edges.append(edge)

    # from_id → [edges] sorted chronologically
    from_to: dict[int, list[dict[str, Any]]] = {}
    for edge in edges:
        from_to.setdefault(edge["from_id"], []).append(edge)
    for lst in from_to.values():
        lst.sort(key=lambda e: e["created_at"])

    # Root snapshots: no edge with a non-null source points to it
    produced_ids: set[int] = {e["to_id"] for e in edges}
    root_ids = [sid for sid in sorted(snap_rows) if sid not in produced_ids]

    visited: set[int] = set()

    def _snap_node(sid: int) -> dict[str, Any]:
        r = snap_rows[sid]
        return {
            "type": "snapshot",
            "id": sid,
            "created_at": r["created_at"],
            "source": r["source"],
            "player_count": r["player_count"],
            "is_latest": sid == latest_id,
            "branches": [],
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

    # Safety net: snapshots unreachable from any root become additional roots
    for sid in sorted(snap_rows):
        if sid not in visited:
            n = _walk(sid)
            if n is not None:
                roots.append(n)

    return {"roots": roots}


async def get_snapshot_detail(session: AsyncSession, snapshot_id: int) -> dict[str, Any] | None:
    """Returns snapshot metadata + player list for the detail panel. None if not found."""
    result = await session.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
    snap = result.scalar_one_or_none()
    if not snap:
        return None

    # Query snapshot history (audit log of in-place edits)
    history_result = await session.execute(
        select(SnapshotHistory)
        .where(SnapshotHistory.snapshot_id == snapshot_id)
        .order_by(SnapshotHistory.created_at.desc())
    )
    history_entries = history_result.scalars().all()

    # Serialize history for the frontend
    history = [
        {
            "id": entry.id,
            "created_at": entry.created_at.isoformat()
            if hasattr(entry.created_at, "isoformat")
            else str(entry.created_at),
            "action_type": entry.action_type,
            "summary": entry.summary,
        }
        for entry in history_entries
    ]

    return {
        "id": snap.id,
        "created_at": snap.created_at.isoformat()
        if hasattr(snap.created_at, "isoformat")
        else str(snap.created_at),
        "source": snap.source,
        "players": await get_snapshot_players(session, snapshot_id),
        "history": history,
    }


async def get_game_event_detail(session: AsyncSession, event_id: int) -> dict[str, Any] | None:
    """Returns full game event detail for the detail panel. None if not found."""
    # Get game event basic info
    ge_query = text("""
        SELECT e.id, e.created_at, e.source_snapshot_id, e.output_snapshot_id,
               gd.attempts, gd.share_text
        FROM   timeline_edges e
        JOIN   game_details gd ON gd.timeline_edge_id = e.id
        WHERE  e.id = :event_id AND e.edge_type = 'game'
    """)
    result = await session.execute(ge_query, {"event_id": event_id})
    ge = result.first()
    if not ge:
        return None

    input_sid = int(ge[2])

    # Get mesas data
    mesas_query = text("""
        SELECT id, table_number, gm_player_id FROM game_tables WHERE timeline_edge_id = :event_id ORDER BY table_number
    """)
    result = await session.execute(mesas_query, {"event_id": event_id})
    mesa_rows = result.all()

    mesas_data: list[dict[str, Any]] = []
    for mesa_row in mesa_rows:
        mesa_id = int(mesa_row[0])
        gm_player_id = mesa_row[2]

        # Get GM name
        gm_name: str | None = None
        if gm_player_id is not None:
            result = await session.execute(select(Player.name).where(Player.id == gm_player_id))
            gm_row = result.scalar_one_or_none()
            gm_name = gm_row if gm_row else None

        # Get players for this mesa
        players_query = text("""
            SELECT p.name, sp.experience, sp.games_this_year, sp.priority,
                   sp.desired_games, sp.gm_games,
                   COALESCE(nc.c_england, 0) AS c_england,
                   COALESCE(nc.c_france, 0) AS c_france,
                   COALESCE(nc.c_germany, 0) AS c_germany,
                   COALESCE(nc.c_italy, 0) AS c_italy,
                   COALESCE(nc.c_austria, 0) AS c_austria,
                   COALESCE(nc.c_russia, 0) AS c_russia,
                   COALESCE(nc.c_turkey, 0) AS c_turkey,
                   mp.country,
                   mp.country_reason
            FROM   table_players mp
            JOIN   players      p  ON p.id  = mp.player_id
            JOIN   snapshot_players sp
                   ON sp.player_id   = mp.player_id
                   AND sp.snapshot_id = :input_sid
            LEFT  JOIN notion_cache nc ON nc.name = p.name
            WHERE  mp.table_id = :mesa_id
            ORDER  BY mp.seat_order
        """)
        result = await session.execute(players_query, {"input_sid": input_sid, "mesa_id": mesa_id})

        jugadores: list[dict[str, Any]] = []
        for p in result.all():
            etiqueta = "Nuevo" if p[1] == "Nuevo" else f"Antiguo ({p[2]} juegos)"
            jugadores.append(
                {
                    "nombre": p[0],
                    "etiqueta": etiqueta,
                    "pais": p[13] or "",  # Convert None to empty string
                    "pais_reason": p[14] if len(p) > 14 else None,
                    "es_nuevo": p[1] == "Nuevo",
                    "experiencia": p[1],
                    "juegos_este_ano": p[2],
                    "prioridad": p[3],
                    "partidas_deseadas": p[4],
                    "partidas_gm": p[5],
                    "c_england": p[6],
                    "c_france": p[7],
                    "c_germany": p[8],
                    "c_italy": p[9],
                    "c_austria": p[10],
                    "c_russia": p[11],
                    "c_turkey": p[12] if len(p) > 12 else 0,
                    "cupos": p[4],  # For backward compatibility
                }
            )

        mesas_data.append(
            {
                "numero": int(mesa_row[1]),
                "gm": gm_name,
                "jugadores": jugadores,
            }
        )

    # Get waiting list
    waiting_query = text("""
        SELECT p.name, wl.missing_spots,
               sp.experience, sp.games_this_year, sp.priority,
               sp.desired_games, sp.gm_games,
               COALESCE(nc.c_england, 0) AS c_england,
               COALESCE(nc.c_france, 0) AS c_france,
               COALESCE(nc.c_germany, 0) AS c_germany,
               COALESCE(nc.c_italy, 0) AS c_italy,
               COALESCE(nc.c_austria, 0) AS c_austria,
               COALESCE(nc.c_russia, 0) AS c_russia,
               COALESCE(nc.c_turkey, 0) AS c_turkey
        FROM   waiting_list wl
        JOIN   players      p ON p.id = wl.player_id
        JOIN   snapshot_players sp
               ON sp.player_id   = wl.player_id
               AND sp.snapshot_id = :input_sid
        LEFT  JOIN notion_cache nc ON nc.name = p.name
        WHERE  wl.timeline_edge_id = :event_id
        ORDER  BY wl.list_order
    """)
    result = await session.execute(waiting_query, {"input_sid": input_sid, "event_id": event_id})

    waiting: list[dict[str, Any]] = []
    for row in result.all():
        waiting.append(
            {
                "nombre": row[0],
                "cupos": f"{row[1]} cupo(s) sin asignar",
                "es_nuevo": row[2] == "Nuevo",
                "experiencia": row[2],
                "juegos_este_ano": row[3],
                "prioridad": row[4],
                "partidas_deseadas": row[5],
                "partidas_gm": row[6],
                "c_england": row[7],
                "c_france": row[8],
                "c_germany": row[9],
                "c_italy": row[10],
                "c_austria": row[11],
                "c_russia": row[12],
                "c_turkey": row[13] if len(row) > 13 else 0,
                "cupos_faltantes": row[5],  # For backward compatibility
            }
        )

    return {
        "id": int(ge[0]),
        "created_at": ge[1],
        "intentos": int(ge[4] or 0),
        "copypaste": ge[5] or "",
        "mesas": mesas_data,
        "waiting_list": waiting,
        "input_snapshot_id": input_sid,
        "output_snapshot_id": int(ge[3]),
    }
