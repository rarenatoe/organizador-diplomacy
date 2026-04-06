"""Async view queries for the REST API.

This module provides async read-only queries for the Diplomacy organizer,
migrating from raw SQLite to SQLAlchemy 2.0 with async sessions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.snapshots import get_deduped_notion_cache_subquery, get_snapshot_players
from backend.db.models import (
    GameDetail,
    GameTable,
    Player,
    Snapshot,
    SnapshotHistory,
    SnapshotPlayer,
    TablePlayer,
    TimelineEdge,
    WaitingList,
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
            "changes": entry.changes,
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
    # Get game event basic info using ORM
    result = await session.execute(
        select(TimelineEdge, GameDetail)
        .join(GameDetail)
        .where(TimelineEdge.id == event_id, TimelineEdge.edge_type == 'game')
    )
    row = result.first()
    if not row:
        return None
    
    timeline_edge, game_detail = row
    input_sid = timeline_edge.source_snapshot_id

    # Get the deduplicated Notion cache subquery
    deduped_cache = get_deduped_notion_cache_subquery(_session=session)

    # Get mesas data using ORM
    mesas_result = await session.execute(
        select(GameTable)
        .where(GameTable.timeline_edge_id == event_id)
        .order_by(GameTable.table_number)
    )
    mesa_rows = mesas_result.scalars().all()

    mesas_data: list[dict[str, Any]] = []
    for mesa in mesa_rows:
        # Get GM name
        gm_name: str | None = None
        if mesa.gm_player_id is not None:
            gm_result = await session.execute(
                select(Player.name).where(Player.id == mesa.gm_player_id)
            )
            gm_name = gm_result.scalar_one_or_none()

        # Get players for this mesa using deduplicated cache
        players_result = await session.execute(
            select(
                Player,
                SnapshotPlayer,
                deduped_cache.c.c_england,
                deduped_cache.c.c_france,
                deduped_cache.c.c_germany,
                deduped_cache.c.c_italy,
                deduped_cache.c.c_austria,
                deduped_cache.c.c_russia,
                deduped_cache.c.c_turkey,
                TablePlayer.country,
                TablePlayer.country_reason,
            )
            .join(TablePlayer, Player.id == TablePlayer.player_id)
            .join(SnapshotPlayer, (SnapshotPlayer.player_id == Player.id) & (SnapshotPlayer.snapshot_id == input_sid))
            .outerjoin(deduped_cache, Player.name == deduped_cache.c.name)
            .where(TablePlayer.table_id == mesa.id)
            .order_by(TablePlayer.seat_order)
        )

        jugadores: list[dict[str, Any]] = []
        for p in players_result.all():
            player, sp, c_england, c_france, c_germany, c_italy, c_austria, c_russia, c_turkey, country, country_reason = p
            etiqueta = "Nuevo" if sp.experience == "Nuevo" else f"Antiguo ({sp.games_this_year} juegos)"
            jugadores.append(
                {
                    "nombre": player.name,
                    "etiqueta": etiqueta,
                    "pais": country or "",  # Convert None to empty string
                    "pais_reason": country_reason,
                    "es_nuevo": sp.experience == "Nuevo",
                    "experiencia": sp.experience,
                    "juegos_este_ano": sp.games_this_year,
                    "prioridad": sp.priority,
                    "partidas_deseadas": sp.desired_games,
                    "partidas_gm": sp.gm_games,
                    "c_england": c_england or 0,
                    "c_france": c_france or 0,
                    "c_germany": c_germany or 0,
                    "c_italy": c_italy or 0,
                    "c_austria": c_austria or 0,
                    "c_russia": c_russia or 0,
                    "c_turkey": c_turkey or 0,
                    "cupos": sp.desired_games,  # For backward compatibility
                }
            )

        mesas_data.append(
            {
                "numero": mesa.table_number,
                "gm": gm_name,
                "jugadores": jugadores,
            }
        )

    # Get waiting list using deduplicated cache
    waiting_result = await session.execute(
        select(
            Player,
            WaitingList,
            SnapshotPlayer,
            deduped_cache.c.c_england,
            deduped_cache.c.c_france,
            deduped_cache.c.c_germany,
            deduped_cache.c.c_italy,
            deduped_cache.c.c_austria,
            deduped_cache.c.c_russia,
            deduped_cache.c.c_turkey,
        )
        .join(WaitingList, Player.id == WaitingList.player_id)
        .join(SnapshotPlayer, (SnapshotPlayer.player_id == Player.id) & (SnapshotPlayer.snapshot_id == input_sid))
        .outerjoin(deduped_cache, Player.name == deduped_cache.c.name)
        .where(WaitingList.timeline_edge_id == event_id)
        .order_by(WaitingList.list_order)
    )

    waiting: list[dict[str, Any]] = []
    for row in waiting_result.all():
        player, wl, sp, c_england, c_france, c_germany, c_italy, c_austria, c_russia, c_turkey = row
        waiting.append(
            {
                "nombre": player.name,
                "cupos": f"{wl.missing_spots} cupo(s) sin asignar",
                "es_nuevo": sp.experience == "Nuevo",
                "experiencia": sp.experience,
                "juegos_este_ano": sp.games_this_year,
                "prioridad": sp.priority,
                "partidas_deseadas": sp.desired_games,
                "partidas_gm": sp.gm_games,
                "c_england": c_england or 0,
                "c_france": c_france or 0,
                "c_germany": c_germany or 0,
                "c_italy": c_italy or 0,
                "c_austria": c_austria or 0,
                "c_russia": c_russia or 0,
                "c_turkey": c_turkey or 0,
                "cupos_faltantes": sp.desired_games,  # For backward compatibility
            }
        )

    return {
        "id": timeline_edge.id,
        "created_at": timeline_edge.created_at,
        "intentos": game_detail.attempts,
        "mesas": mesas_data,
        "waiting_list": waiting,
        "input_snapshot_id": input_sid,
        "output_snapshot_id": timeline_edge.output_snapshot_id,
    }
