"""Snapshot-related CRUD operations.

This module contains database operations for snapshot management,
Notion cache, and history logging, extracted from the monolithic crud.py file
for better organization.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.chain import create_timeline_edge
from backend.crud.players import get_or_create_player
from backend.db.models import (
    DeepDiffResult,
    FieldChange,
    GameDetail,
    GameTable,
    GraphNode,
    ModifiedPlayer,
    NotionCache,
    Player,
    RenameDict,
    Snapshot,
    SnapshotHistory,
    SnapshotPlayer,
    TablePlayer,
    TimelineEdge,
    WaitingList,
)

# ── Diffing Logic ────────────────────────────────────────────────────────────


def generate_deep_diff(
    old_players: list[dict[str, Any]],
    new_players: list[dict[str, Any]],
    renames: list[RenameDict],
) -> DeepDiffResult:
    """Generate a structured changes object comparing old and new player lists with rename handling."""
    # Create lookup dictionaries by player name
    old_dict = {p["nombre"]: p for p in old_players}
    new_dict = {p["nombre"]: p for p in new_players}

    # Apply renames to old_dict: update keys from old names to new names
    for rename in renames:
        old_name = rename["from"]
        new_name = rename["to"]
        if old_name in old_dict:
            old_dict[new_name] = old_dict.pop(old_name)

    # Find added, removed, and common players
    added_names = set(new_dict.keys()) - set(old_dict.keys())
    removed_names = set(old_dict.keys()) - set(new_dict.keys())
    common_names = set(old_dict.keys()) & set(new_dict.keys())

    added: list[str] = sorted(added_names)
    removed: list[str] = sorted(removed_names)
    modified: list[ModifiedPlayer] = []

    # Check for modified players - compare ALL keys
    for name in sorted(common_names):
        old = old_dict[name]
        new = new_dict[name]

        field_changes: dict[str, FieldChange] = {}

        # Get all unique keys from both dictionaries
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            if key == "nombre":
                continue  # Skip the name field itself

            old_value = old.get(key)
            new_value = new.get(key)

            if old_value != new_value:
                field_changes[key] = {"old": old_value, "new": new_value}

        if field_changes:
            modified.append({"nombre": name, "changes": field_changes})

    return {
        "added": added,
        "removed": removed,
        "renamed": renames,
        "modified": modified,
    }

# ── Players ────────────────────────────────────────────────────────────────────

# Player operations moved to backend.crud.players module


async def add_player_to_snapshot(
    session: AsyncSession,
    snapshot_id: int,
    player_id: int,
    experience: str,
    games_this_year: int,
    priority: int,
    desired_games: int,
    gm_games: int,
) -> None:
    """Link a player to a snapshot with game data."""
    sp = SnapshotPlayer(
        snapshot_id=snapshot_id,
        player_id=player_id,
        experience=experience,
        games_this_year=games_this_year,
        priority=priority,
        desired_games=desired_games,
        gm_games=gm_games,
    )
    session.add(sp)


# ── Snapshots ────────────────────────────────────────────────────────────────


async def create_snapshot(session: AsyncSession, source: str) -> int:
    """Create a new snapshot and return its ID."""
    # Create graph node
    node = GraphNode(entity_type="snapshot")
    session.add(node)
    await session.flush()
    node_id = node.id

    # Create snapshot
    snapshot = Snapshot(id=node_id, source=source)
    session.add(snapshot)
    await session.flush()
    return snapshot.id


async def get_latest_snapshot_id(session: AsyncSession) -> int | None:
    """Returns the id of the most recently created snapshot, or None."""
    result = await session.execute(select(func.max(Snapshot.id)))
    val = result.scalar()
    return int(val) if val is not None else None


async def snapshots_have_same_roster(
    session: AsyncSession,
    snapshot_id: int,
    notion_rows: list[dict[str, Any]],
) -> bool:
    """
    Compare snapshot roster with Notion data.
    Returns True if rosters match (ignoring order and extra fields).
    """
    # Get snapshot players with player names
    result = await session.execute(
        select(SnapshotPlayer, Player).join(Player).where(SnapshotPlayer.snapshot_id == snapshot_id)
    )
    rows = result.all()

    # Build comparison dict
    snap_dict: dict[str, dict[str, Any]] = {
        player.name: {
            "experiencia": sp.experience,
            "juegos_este_ano": sp.games_this_year,
            "prioridad": sp.priority,
            "partidas_deseadas": sp.desired_games,
            "partidas_gm": sp.gm_games,
        }
        for sp, player in rows
    }

    # Build notion dict
    notion_dict: dict[str, dict[str, Any]] = {
        r["nombre"]: {
            "experiencia": r["experiencia"],
            "juegos_este_ano": int(r["juegos_este_ano"]),
            "prioridad": int(r.get("prioridad", 0)),
            "partidas_deseadas": int(r.get("partidas_deseadas", 1)),
            "partidas_gm": int(r.get("partidas_gm", 0)),
        }
        for r in notion_rows
    }

    return snap_dict == notion_dict


async def get_snapshot_players(session: AsyncSession, snapshot_id: int) -> list[dict[str, Any]]:
    """Return all players in a snapshot as dictionaries."""
    # Get the deduplicated Notion cache subquery
    deduped_cache = get_deduped_notion_cache_subquery(_session=session)

    result = await session.execute(
        select(
            SnapshotPlayer,
            Player,
            deduped_cache.c.c_england,
            deduped_cache.c.c_france,
            deduped_cache.c.c_germany,
            deduped_cache.c.c_italy,
            deduped_cache.c.c_austria,
            deduped_cache.c.c_russia,
            deduped_cache.c.c_turkey,
        )
        .join(Player)
        .outerjoin(deduped_cache, Player.name == deduped_cache.c.name)
        .where(SnapshotPlayer.snapshot_id == snapshot_id)
        .order_by(SnapshotPlayer.priority.desc(), Player.name)
    )
    rows = result.all()

    return [
        {
            "nombre": player.name,
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
        }
        for sp, player, c_england, c_france, c_germany, c_italy, c_austria, c_russia, c_turkey in rows
    ]


# ── Events ───────────────────────────────────────────────────────────────────

# Timeline edge operations moved to backend.crud.chain module


async def delete_snapshot_cascade(session: AsyncSession, snapshot_id: int) -> bool:
    """Delete a snapshot and all its dependent data."""
    # Delete snapshot history logs
    await session.execute(delete(SnapshotHistory).where(SnapshotHistory.snapshot_id == snapshot_id))

    # Delete snapshot players
    await session.execute(delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id))

    # Delete incoming timeline edges (where this snapshot is output)
    result = await session.execute(
        select(TimelineEdge).where(TimelineEdge.output_snapshot_id == snapshot_id)
    )
    incoming_edges = result.scalars().all()

    for edge in incoming_edges:
        # Delete edge details
        await session.execute(delete(GameDetail).where(GameDetail.timeline_edge_id == edge.id))

        # Delete game tables
        result = await session.execute(
            select(GameTable).where(GameTable.timeline_edge_id == edge.id)
        )
        tables = result.scalars().all()

        for table in tables:
            # Delete table players
            await session.execute(delete(TablePlayer).where(TablePlayer.table_id == table.id))

        await session.execute(delete(GameTable).where(GameTable.timeline_edge_id == edge.id))

        # Delete waiting list
        await session.execute(delete(WaitingList).where(WaitingList.timeline_edge_id == edge.id))

        # Delete the timeline edge itself
        await session.execute(delete(TimelineEdge).where(TimelineEdge.id == edge.id))

        # Delete graph node
        await session.execute(delete(GraphNode).where(GraphNode.id == edge.id))

    # Delete outgoing timeline edges (where this snapshot is source)
    result = await session.execute(
        select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snapshot_id)
    )
    outgoing_edges = result.scalars().all()

    for edge in outgoing_edges:
        # Delete edge details
        await session.execute(delete(GameDetail).where(GameDetail.timeline_edge_id == edge.id))

        # Delete game tables
        result = await session.execute(
            select(GameTable).where(GameTable.timeline_edge_id == edge.id)
        )
        tables = result.scalars().all()

        for table in tables:
            # Delete table players
            await session.execute(delete(TablePlayer).where(TablePlayer.table_id == table.id))

        await session.execute(delete(GameTable).where(GameTable.timeline_edge_id == edge.id))

        # Delete waiting list
        await session.execute(delete(WaitingList).where(WaitingList.timeline_edge_id == edge.id))

        # Delete the timeline edge itself
        await session.execute(delete(TimelineEdge).where(TimelineEdge.id == edge.id))

        # Delete graph node
        await session.execute(delete(GraphNode).where(GraphNode.id == edge.id))

    # Delete snapshot
    await session.execute(delete(Snapshot).where(Snapshot.id == snapshot_id))

    # Delete graph node
    await session.execute(delete(GraphNode).where(GraphNode.id == snapshot_id))

    return True


# ── Game Organization ─────────────────────────────────────────────────────────


async def create_manual_snapshot(
    session: AsyncSession,
    source_snapshot_id: int,
    edits: list[dict[str, Any]],
) -> int:
    """Create a manual snapshot with edited player data."""
    source_players: dict[str, dict[str, Any]] = {
        p["nombre"]: p for p in await get_snapshot_players(session, source_snapshot_id)
    }
    snap_id = await create_snapshot(session, "manual")

    for e in edits:
        nombre = e["nombre"]
        base = source_players.get(nombre)
        if base is None:
            continue

        result = await session.execute(select(Player).where(Player.name == nombre))
        player: Player | None = result.scalar_one_or_none()
        if not player:
            continue

        await add_player_to_snapshot(
            session,
            snap_id,
            player.id,
            base["experiencia"],
            base["juegos_este_ano"],
            int(e.get("prioridad", base["prioridad"])),
            int(e.get("partidas_deseadas", base["partidas_deseadas"])),
            int(e.get("partidas_gm", base["partidas_gm"])),
        )

    # Create event
    await create_timeline_edge(session, "manual", source_snapshot_id, snap_id)
    return snap_id


async def create_root_manual_snapshot(
    session: AsyncSession,
    players: list[dict[str, Any]],
) -> int:
    """Create a manual snapshot from scratch (no source)."""
    snap_id = await create_snapshot(session, "manual")

    for p in players:
        if not p["nombre"]:
            continue
        player_id = await get_or_create_player(session, p["nombre"])
        await add_player_to_snapshot(
            session,
            snap_id,
            player_id,
            p["experiencia"],
            int(p["juegos_este_ano"]),
            int(p.get("prioridad", 0)),
            int(p.get("partidas_deseadas", 1)),
            int(p.get("partidas_gm", 0)),
        )

    return snap_id


# ── Notion Cache ─────────────────────────────────────────────────────────────


def get_deduped_notion_cache_subquery(_session: AsyncSession):
    """Create a reusable SQLAlchemy subquery to deduplicate Notion cache entries.
    
    Returns a subquery that groups by NotionCache.name and selects the maximum
    values for country assignments and other fields to prevent fan-out bugs.
    """
    return (
        select(
            NotionCache.name,
            func.max(NotionCache.c_austria).label("c_austria"),
            func.max(NotionCache.c_england).label("c_england"),
            func.max(NotionCache.c_france).label("c_france"),
            func.max(NotionCache.c_germany).label("c_germany"),
            func.max(NotionCache.c_italy).label("c_italy"),
            func.max(NotionCache.c_russia).label("c_russia"),
            func.max(NotionCache.c_turkey).label("c_turkey"),
            func.max(NotionCache.experience).label("experience"),
            func.max(NotionCache.games_this_year).label("games_this_year"),
        )
        .group_by(NotionCache.name)
        .subquery()
    )


async def update_notion_cache(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """Update the Notion cache with fresh data."""
    # Clear existing cache
    await session.execute(delete(NotionCache))

    # Insert new cache entries
    for r in rows:
        cache = NotionCache(
            notion_id=r["notion_id"],
            name=r["nombre"],
            experience=r["experiencia"],
            games_this_year=int(r["juegos_este_ano"]),
            c_england=int(r.get("c_england", 0)),
            c_france=int(r.get("c_france", 0)),
            c_germany=int(r.get("c_germany", 0)),
            c_italy=int(r.get("c_italy", 0)),
            c_austria=int(r.get("c_austria", 0)),
            c_russia=int(r.get("c_russia", 0)),
            c_turkey=int(r.get("c_turkey", 0)),
            alias=r.get("alias", []),
            last_updated=datetime.now(),
        )
        session.add(cache)


async def get_notion_cache(session: AsyncSession) -> list[dict[str, Any]]:
    """Get all cached Notion data."""
    result = await session.execute(select(NotionCache).order_by(NotionCache.name))
    rows = result.scalars().all()

    return [
        {
            "notion_id": r.notion_id,
            "nombre": r.name,
            "experiencia": r.experience,
            "juegos_este_ano": r.games_this_year,
            "c_england": r.c_england,
            "c_france": r.c_france,
            "c_germany": r.c_germany,
            "c_italy": r.c_italy,
            "c_austria": r.c_austria,
            "c_russia": r.c_russia,
            "c_turkey": r.c_turkey,
            "alias": r.alias,
            "last_updated": r.last_updated,
        }
        for r in rows
    ]


# ── Mesa Management ─────────────────────────────────────────────────────────

# Game table operations moved to backend.crud.games module


# ── History Logging ─────────────────────────────────────────────────────────────


async def log_snapshot_history(
    session: AsyncSession,
    snapshot_id: int,
    action_type: str,
    changes: DeepDiffResult,
    previous_state: dict[str, object],
) -> None:
    """Log a snapshot history entry."""
    history_entry = SnapshotHistory(
        snapshot_id=snapshot_id,
        action_type=action_type,
        changes=changes,
        previous_state=previous_state,
    )
    session.add(history_entry)
