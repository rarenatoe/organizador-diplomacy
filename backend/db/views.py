"""Async view queries for the REST API.

This module provides async read-only queries for the Diplomacy organizer,
migrating from raw SQLite to SQLAlchemy 2.0 with async sessions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from pydantic import ValidationError
from sqlalchemy import select, text

from backend.api.models.chain import Branch, ChainEdge, ChainResponse, SnapshotNode
from backend.api.models.games import (  # noqa: TC001
    CountrySelection,
    GameDetailResponse,
    GameDraftPlayer,
    GameDraftTable,
)
from backend.api.models.snapshots import DeepDiffResult, HistoryEntry, SnapshotDetailResponse
from backend.core.logger import logger
from backend.crud.snapshots import get_snapshot_players
from backend.db.models import (
    GameDetail,
    GameTable,
    Player,
    Snapshot,
    SnapshotHistory,
    SnapshotPlayer,
    SnapshotSource,
    TablePlayer,
    TimelineEdge,
    WaitingList,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _normalize_snapshot_source(raw_source: SnapshotSource | str) -> SnapshotSource:
    """Normalize DB enum payloads to SnapshotSource-compatible values."""
    if isinstance(raw_source, SnapshotSource):
        return raw_source

    # SQLAlchemy/SQLite raw queries can return enum names (e.g. NOTION_SYNC)
    # instead of enum values (e.g. notion_sync).
    return SnapshotSource(raw_source.lower())


class ChainSnapshotRow(TypedDict):
    id: int
    created_at: str
    source: SnapshotSource
    player_count: int


async def build_chain_data(session: AsyncSession) -> ChainResponse:
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
    snap_rows: dict[int, ChainSnapshotRow] = {}
    for r in result.all():
        snapshot_id = int(r[0])
        created_at = r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]).replace(" ", "T")
        snap_rows[snapshot_id] = {
            "id": snapshot_id,
            "created_at": created_at,
            "source": _normalize_snapshot_source(r[2]),
            "player_count": int(r[3]),
        }

    if not snap_rows:
        return ChainResponse(roots=[])

    latest_id = max(snap_rows)

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

    rows = result.mappings().all()

    edges: list[ChainEdge] = []
    for r in rows:
        edge = ChainEdge(
            type=r["edge_type"],
            id=int(r["id"]),
            created_at=r["created_at"].isoformat()
            if hasattr(r["created_at"], "isoformat")
            else str(r["created_at"]).replace(" ", "T"),
            from_id=int(r["source_snapshot_id"]),
            to_id=r["output_snapshot_id"],
        )
        if r["edge_type"] == "game":
            edge.intentos = r["attempts"] or 0
            edge.mesa_count = r["mesa_count"]
            edge.espera_count = r["espera_count"]
        edges.append(edge)

    # from_id → [edges] sorted chronologically
    from_to: dict[int, list[ChainEdge]] = {}
    for edge in edges:
        from_to.setdefault(edge.from_id, []).append(edge)
    for lst in from_to.values():
        lst.sort(key=lambda e: e.created_at)

    # Root snapshots: no edge with a non-null source points to it
    produced_ids: set[int] = {e.to_id for e in edges if e.to_id is not None}
    root_ids = [sid for sid in sorted(snap_rows) if sid not in produced_ids]

    visited: set[int] = set()

    def _snap_node(sid: int) -> SnapshotNode:
        r = snap_rows[sid]
        return SnapshotNode(
            type="snapshot",
            id=sid,
            created_at=r["created_at"],
            source=r["source"],
            player_count=r["player_count"],
            is_latest=sid == latest_id,
            branches=[],
        )

    def _walk(sid: int) -> SnapshotNode | None:
        if sid not in snap_rows or sid in visited:
            return None
        visited.add(sid)
        node = _snap_node(sid)
        for edge in from_to.get(sid, []):
            output = _walk(edge.to_id) if edge.to_id else None
            node.branches.append(Branch(edge=edge, output=output))
        return node

    roots: list[SnapshotNode] = []
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

    return ChainResponse(roots=roots)


async def get_snapshot_detail(
    session: AsyncSession, snapshot_id: int
) -> SnapshotDetailResponse | None:
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
    history: list[HistoryEntry] = []
    for entry in history_entries:
        try:
            history.append(
                HistoryEntry(
                    id=entry.id,
                    created_at=entry.created_at,
                    action_type=entry.action_type,
                    changes=DeepDiffResult.model_validate(entry.changes),
                )
            )
        except ValidationError:
            logger.warning(
                "Skipping malformed snapshot history entry",
                exc_info=True,
                extra={"snapshot_id": snapshot_id, "history_id": entry.id},
            )

    return SnapshotDetailResponse(
        id=snap.id,
        created_at=snap.created_at,
        source=snap.source,
        players=await get_snapshot_players(session, snapshot_id),
        history=history,
    )


def _format_created_at(raw: Any) -> str:
    """Normalize datetime or string to ISO-like format."""
    if hasattr(raw, "isoformat"):
        return raw.isoformat()
    return str(raw).replace(" ", "T")


async def get_game_event_detail(session: AsyncSession, event_id: int) -> GameDetailResponse | None:
    """Returns full game event detail for the detail panel. None if not found."""
    # Get game event basic info using ORM
    result = await session.execute(
        select(TimelineEdge, GameDetail)
        .join(GameDetail)
        .where(TimelineEdge.id == event_id, TimelineEdge.edge_type == "game")
    )
    row = result.first()
    if not row:
        return None

    timeline_edge, game_detail = row
    input_sid = timeline_edge.source_snapshot_id

    # Get mesas data using ORM
    mesas_result = await session.execute(
        select(GameTable)
        .where(GameTable.timeline_edge_id == event_id)
        .order_by(GameTable.table_number)
    )
    mesa_rows = mesas_result.scalars().all()

    mesas_data: list[GameDraftTable] = []
    for mesa in mesa_rows:
        # Get GM player data
        gm_player: GameDraftPlayer | None = None
        if mesa.gm_player_id is not None:
            gm_result = await session.execute(
                select(
                    Player,
                    SnapshotPlayer,
                )
                .join(
                    SnapshotPlayer,
                    (SnapshotPlayer.player_id == Player.id)
                    & (SnapshotPlayer.snapshot_id == input_sid),
                )
                .where(Player.id == mesa.gm_player_id)
            )
            gm_row = gm_result.first()
            if gm_row:
                gm_p, gm_sp = gm_row
                gm_player = GameDraftPlayer(
                    nombre=gm_p.name,
                    is_new=gm_sp.is_new,
                    juegos_este_ano=gm_sp.games_this_year,
                    has_priority=gm_sp.has_priority,
                    partidas_deseadas=gm_sp.desired_games,
                    partidas_gm=gm_sp.gm_games,
                    c_england=0,
                    c_france=0,
                    c_germany=0,
                    c_italy=0,
                    c_austria=0,
                    c_russia=0,
                    c_turkey=0,
                    country=CountrySelection(name="", reason=""),
                )

        # Get players for this mesa
        players_result = await session.execute(
            select(
                Player,
                SnapshotPlayer,
                TablePlayer.country,
                TablePlayer.country_reason,
            )
            .join(TablePlayer, Player.id == TablePlayer.player_id)
            .join(
                SnapshotPlayer,
                (SnapshotPlayer.player_id == Player.id) & (SnapshotPlayer.snapshot_id == input_sid),
            )
            .where(TablePlayer.table_id == mesa.id)
            .order_by(TablePlayer.seat_order)
        )

        jugadores: list[GameDraftPlayer] = []
        for p in players_result.all():
            player, sp, country, country_reason = p
            jugadores.append(
                GameDraftPlayer(
                    nombre=player.name,
                    is_new=sp.is_new,
                    juegos_este_ano=sp.games_this_year,
                    has_priority=sp.has_priority,
                    partidas_deseadas=sp.desired_games,
                    partidas_gm=sp.gm_games,
                    c_england=0,
                    c_france=0,
                    c_germany=0,
                    c_italy=0,
                    c_austria=0,
                    c_russia=0,
                    c_turkey=0,
                    country=CountrySelection(
                        name=country or "",
                        reason=country_reason or "",
                    ),
                )
            )

        mesas_data.append(
            GameDraftTable(
                numero=mesa.table_number,
                gm=gm_player,
                jugadores=jugadores,
            )
        )

    # Get waiting list
    waiting_result = await session.execute(
        select(
            Player,
            SnapshotPlayer,
        )
        .join(WaitingList, Player.id == WaitingList.player_id)
        .join(
            SnapshotPlayer,
            (SnapshotPlayer.player_id == Player.id) & (SnapshotPlayer.snapshot_id == input_sid),
        )
        .where(WaitingList.timeline_edge_id == event_id)
        .order_by(WaitingList.list_order)
    )

    waiting: list[GameDraftPlayer] = []
    for row in waiting_result.all():
        player, sp = row
        waiting.append(
            GameDraftPlayer(
                nombre=player.name,
                is_new=sp.is_new,
                juegos_este_ano=sp.games_this_year,
                has_priority=sp.has_priority,
                partidas_deseadas=sp.desired_games,
                partidas_gm=sp.gm_games,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
                country=CountrySelection(name="", reason=""),
                cupos_faltantes=sp.desired_games,
            )
        )

    return GameDetailResponse(
        id=timeline_edge.id,
        created_at=_format_created_at(timeline_edge.created_at),
        intentos=game_detail.attempts,
        mesas=mesas_data,
        waiting_list=waiting,
        input_snapshot_id=input_sid,
        output_snapshot_id=timeline_edge.output_snapshot_id,
    )
