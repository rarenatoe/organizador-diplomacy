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

from backend.api.models.snapshots import (
    DeepDiffResult,
    FieldChange,
    FieldValue,
    HistoryState,
    ModifiedPlayer,
    PlayerData,
    RenameChange,
)
from backend.db.models import (
    GameDetail,
    GameTable,
    GraphNode,
    NotionCache,
    Player,
    Snapshot,
    SnapshotHistory,
    SnapshotPlayer,
    SnapshotSource,
    TablePlayer,
    TimelineEdge,
    WaitingList,
)

# ── Diffing Logic ────────────────────────────────────────────────────────────


def generate_deep_diff(
    old_players: list[dict[str, Any]],
    new_players: list[dict[str, Any]],
    renames: list[RenameChange],
) -> DeepDiffResult:
    """Generate a structured changes object comparing old and new player lists with rename handling."""
    # Create lookup dictionaries by player name
    old_dict = {p["nombre"]: p for p in old_players}
    new_dict = {p["nombre"]: p for p in new_players}

    # Apply renames to old_dict: update keys from old names to new names
    for rename in renames:
        old_name = rename.old_name
        new_name = rename.new_name
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
                field_changes[key] = FieldChange(
                    old=FieldValue(old_value), new=FieldValue(new_value)
                )

        if field_changes:
            modified.append(ModifiedPlayer(nombre=name, changes=field_changes))

    return DeepDiffResult(
        added=added,
        removed=removed,
        renamed=renames,
        modified=modified,
    )


# ── Players ────────────────────────────────────────────────────────────────────

# Player operations moved to backend.crud.players module


async def add_player_to_snapshot(
    session: AsyncSession,
    snapshot_id: int,
    player_id: int,
    games_this_year: int,
    desired_games: int,
    gm_games: int,
    *,
    has_priority: bool,
    is_new: bool,
) -> None:
    """Link a player to a snapshot with game data."""
    sp = SnapshotPlayer(
        snapshot_id=snapshot_id,
        player_id=player_id,
        is_new=is_new,
        games_this_year=games_this_year,
        has_priority=has_priority,
        desired_games=desired_games,
        gm_games=gm_games,
    )
    session.add(sp)


# ── Snapshots ────────────────────────────────────────────────────────────────


async def create_snapshot(session: AsyncSession, source: SnapshotSource) -> int:
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
            "is_new": sp.is_new,
            "juegos_este_ano": sp.games_this_year,
            "has_priority": sp.has_priority,
            "partidas_deseadas": sp.desired_games,
            "partidas_gm": sp.gm_games,
        }
        for sp, player in rows
    }

    # Build notion dict
    notion_dict: dict[str, dict[str, Any]] = {
        r["nombre"]: {
            "is_new": r["is_new"],
            "juegos_este_ano": int(r["juegos_este_ano"]),
            "has_priority": bool(r.get("has_priority", False)),
            "partidas_deseadas": int(r.get("partidas_deseadas", 1)),
            "partidas_gm": int(r.get("partidas_gm", 0)),
        }
        for r in notion_rows
    }

    return snap_dict == notion_dict


async def get_snapshot_players(session: AsyncSession, snapshot_id: int) -> list[PlayerData]:
    """Return all players in a snapshot as dictionaries with Notion identity data."""
    result = await session.execute(
        select(
            SnapshotPlayer,
            Player,
            NotionCache.name.label("notion_name"),
            NotionCache.c_england,
            NotionCache.c_france,
            NotionCache.c_germany,
            NotionCache.c_italy,
            NotionCache.c_austria,
            NotionCache.c_russia,
            NotionCache.c_turkey,
        )
        .join(Player)
        .outerjoin(NotionCache, NotionCache.notion_id == Player.notion_id)
        .where(SnapshotPlayer.snapshot_id == snapshot_id)
        .order_by(SnapshotPlayer.has_priority.desc(), Player.name)
    )
    rows = result.all()

    return [
        PlayerData(
            nombre=player.name,
            notion_id=player.notion_id,
            notion_name=notion_name,
            is_new=sp.is_new,
            juegos_este_ano=sp.games_this_year,
            has_priority=sp.has_priority,
            partidas_deseadas=sp.desired_games,
            partidas_gm=sp.gm_games,
            c_england=c_england or 0,
            c_france=c_france or 0,
            c_germany=c_germany or 0,
            c_italy=c_italy or 0,
            c_austria=c_austria or 0,
            c_russia=c_russia or 0,
            c_turkey=c_turkey or 0,
            alias=None,
        )
        for sp, player, notion_name, c_england, c_france, c_germany, c_italy, c_austria, c_russia, c_turkey in rows
    ]


# ── Events ───────────────────────────────────────────────────────────────────

# Timeline edge operations moved to backend.crud.chain module


async def delete_timeline_edge_cascade(session: AsyncSession, edge_id: int) -> None:
    """Helper: Deletes a timeline edge and all its dependent game/table data."""

    # 1. Bulk delete all TablePlayers for all tables in this edge (Fixes N+1 issue)
    table_subquery = select(GameTable.id).where(GameTable.timeline_edge_id == edge_id)
    await session.execute(delete(TablePlayer).where(TablePlayer.table_id.in_(table_subquery)))

    # 2. Delete the remaining edge dependencies
    await session.execute(delete(GameTable).where(GameTable.timeline_edge_id == edge_id))
    await session.execute(delete(GameDetail).where(GameDetail.timeline_edge_id == edge_id))
    await session.execute(delete(WaitingList).where(WaitingList.timeline_edge_id == edge_id))

    # 3. Delete the edge itself and its graph node
    await session.execute(delete(TimelineEdge).where(TimelineEdge.id == edge_id))
    await session.execute(delete(GraphNode).where(GraphNode.id == edge_id))


async def delete_snapshot_cascade(session: AsyncSession, snapshot_id: int) -> bool:
    """Delete a snapshot and all its dependent data recursively."""

    # 1. Clean up simple Snapshot-specific tables
    await session.execute(delete(SnapshotHistory).where(SnapshotHistory.snapshot_id == snapshot_id))
    await session.execute(delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id))

    # 2. Recursively delete child snapshots (this automatically handles outgoing edges)
    # We only fetch the IDs, not the full ORM objects.
    result = await session.execute(
        select(TimelineEdge.output_snapshot_id).where(
            TimelineEdge.source_snapshot_id == snapshot_id
        )
    )
    child_snapshot_ids = result.scalars().all()

    for child_id in child_snapshot_ids:
        await delete_snapshot_cascade(session, child_id)

    # 3. Clean up incoming edges (the link between our parent and us)
    result = await session.execute(
        select(TimelineEdge.id).where(TimelineEdge.output_snapshot_id == snapshot_id)
    )
    incoming_edge_ids = result.scalars().all()

    for edge_id in incoming_edge_ids:
        await delete_timeline_edge_cascade(session, edge_id)

    # 4. Finally, delete the snapshot itself and its graph node
    await session.execute(delete(Snapshot).where(Snapshot.id == snapshot_id))
    await session.execute(delete(GraphNode).where(GraphNode.id == snapshot_id))

    return True


# ── Notion Cache ─────────────────────────────────────────────────────────────


async def update_notion_cache(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """Update the Notion cache with fresh data."""
    # Clear existing cache
    await session.execute(delete(NotionCache))

    # Insert new cache entries
    for r in rows:
        cache = NotionCache(
            notion_id=r["notion_id"],
            name=r["nombre"],
            is_new=r["is_new"],
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
            "is_new": r.is_new,
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
    action_type: SnapshotSource,
    changes: DeepDiffResult,
    previous_state: HistoryState,
) -> None:
    """Log a snapshot history entry."""
    history_entry = SnapshotHistory(
        snapshot_id=snapshot_id,
        action_type=action_type,
        changes=changes.model_dump(mode="json"),
        previous_state=previous_state.model_dump(),
    )
    session.add(history_entry)
