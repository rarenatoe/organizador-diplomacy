"""Async CRUD operations using SQLAlchemy.

This module provides async database operations for the Diplomacy organizer,
migrating from raw SQLite to SQLAlchemy 2.0 with async sessions.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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

if TYPE_CHECKING:
    from backend.organizador.models import DraftResult


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


async def get_or_create_player(session: AsyncSession, name: str) -> int:
    """Returns the player id, inserting a new row if the name is unknown."""
    result = await session.execute(select(Player).where(Player.name == name))
    player = result.scalar_one_or_none()
    if player:
        return player.id

    new_player: Player = Player(name=name)
    session.add(new_player)
    await session.flush()
    return new_player.id


async def rename_player(session: AsyncSession, old_name: str, new_name: str) -> bool:
    """
    Renames a player. If new_name already exists, links snapshot_players
    to the existing player and deletes the old player if orphaned.
    Returns True if successful.
    """
    # Check if old name exists
    result = await session.execute(select(Player).where(Player.name == old_name))
    old_player = result.scalar_one_or_none()
    if not old_player:
        return False

    old_id = old_player.id

    # Check if new name already exists
    result = await session.execute(select(Player).where(Player.name == new_name))
    new_player = result.scalar_one_or_none()

    if new_player:
        new_id = new_player.id

        # Check if both players are in the same snapshot
        result = await session.execute(
            select(SnapshotPlayer.snapshot_id).where(SnapshotPlayer.player_id == old_id).distinct()
        )
        old_snapshots = result.scalars().all()

        for snapshot_id in old_snapshots:
            result = await session.execute(
                select(SnapshotPlayer)
                .where(SnapshotPlayer.snapshot_id == snapshot_id)
                .where(SnapshotPlayer.player_id == new_id)
            )
            if result.scalar_one_or_none():
                # New name is already in the same snapshot - block the rename
                return False

        # Update snapshot_players to point to the existing player
        await session.execute(
            update(SnapshotPlayer)
            .where(SnapshotPlayer.player_id == old_id)
            .values(player_id=new_id)
        )

        # Handle table_players conflicts
        result = await session.execute(
            select(TablePlayer.table_id).where(TablePlayer.player_id == new_id)
        )
        new_player_tables = {row for row in result.scalars().all()}

        if new_player_tables:
            await session.execute(
                delete(TablePlayer)
                .where(TablePlayer.player_id == old_id)
                .where(TablePlayer.table_id.in_(new_player_tables))
            )

        await session.execute(
            update(TablePlayer).where(TablePlayer.player_id == old_id).values(player_id=new_id)
        )

        # Update other references
        await session.execute(
            update(GameTable).where(GameTable.gm_player_id == old_id).values(gm_player_id=new_id)
        )
        await session.execute(
            update(WaitingList).where(WaitingList.player_id == old_id).values(player_id=new_id)
        )

        # Check if old player is orphaned
        result = await session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.player_id == old_id).limit(1)
        )
        has_snapshot_links = result.scalar_one_or_none() is not None

        result = await session.execute(
            select(GameTable).where(GameTable.gm_player_id == old_id).limit(1)
        )
        has_gm_links = result.scalar_one_or_none() is not None

        result = await session.execute(
            select(TablePlayer).where(TablePlayer.player_id == old_id).limit(1)
        )
        has_table_links = result.scalar_one_or_none() is not None

        result = await session.execute(
            select(WaitingList).where(WaitingList.player_id == old_id).limit(1)
        )
        has_waiting_links = result.scalar_one_or_none() is not None

        if not any([has_snapshot_links, has_gm_links, has_table_links, has_waiting_links]):
            await session.execute(delete(Player).where(Player.id == old_id))

        return True
    else:
        # Simple rename
        old_player.name = new_name
        return True


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
    from sqlalchemy import func

    # Use aggregate functions to handle multiple NotionCache entries
    # This prevents fan-out when a player has multiple cache rows
    result = await session.execute(
        select(
            SnapshotPlayer,
            Player,
            func.max(NotionCache.c_england).label("c_england"),
            func.max(NotionCache.c_france).label("c_france"),
            func.max(NotionCache.c_germany).label("c_germany"),
            func.max(NotionCache.c_italy).label("c_italy"),
            func.max(NotionCache.c_austria).label("c_austria"),
            func.max(NotionCache.c_russia).label("c_russia"),
            func.max(NotionCache.c_turkey).label("c_turkey"),
        )
        .join(Player)
        .outerjoin(NotionCache, Player.name == NotionCache.name)
        .where(SnapshotPlayer.snapshot_id == snapshot_id)
        .group_by(SnapshotPlayer.player_id, Player.id)
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


async def create_timeline_edge(
    session: AsyncSession,
    edge_type: str,
    source_snapshot_id: int | None,
    output_snapshot_id: int,
) -> int:
    """Create a new timeline edge and return its ID."""
    # Create graph node
    node = GraphNode(entity_type="timeline_edge")
    session.add(node)
    await session.flush()
    node_id = node.id

    # Create timeline edge
    edge = TimelineEdge(
        id=node_id,
        edge_type=edge_type,
        source_snapshot_id=source_snapshot_id,
        output_snapshot_id=output_snapshot_id,
    )
    session.add(edge)
    await session.flush()
    return edge.id


async def create_branch_edge(
    session: AsyncSession, source_snapshot_id: int, output_snapshot_id: int
) -> int:
    """Create a branch edge."""
    return await create_timeline_edge(session, "branch", source_snapshot_id, output_snapshot_id)


async def squash_linear_branch(session: AsyncSession, snapshot_id: int) -> None:
    """
    Squashes linear branch chains into a single snapshot.
    If a snapshot has EXACTLY ONE outgoing edge, and that edge is NOT a game,
    this function absorbs the child snapshot into the parent.
    """
    from sqlalchemy import delete, select, update

    from backend.db.models import GraphNode, Snapshot, SnapshotHistory, SnapshotPlayer, TimelineEdge

    # Query outgoing edges from this snapshot
    result = await session.execute(
        select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snapshot_id)
    )
    outgoing_edges = result.scalars().all()

    # Only squash if exactly 1 outgoing edge and it's NOT a game
    if len(outgoing_edges) != 1:
        return

    edge = outgoing_edges[0]
    if edge.edge_type == "game":
        return

    child_id = edge.output_snapshot_id

    # Step 0: Inherit source and timestamp from child
    child_snap_result = await session.execute(select(Snapshot).where(Snapshot.id == child_id))
    child_snap = child_snap_result.scalar_one()
    await session.execute(
        update(Snapshot)
        .where(Snapshot.id == snapshot_id)
        .values(source=child_snap.source, created_at=child_snap.created_at)
    )

    # Step 1: Move child's outgoing edges to parent
    await session.execute(
        update(TimelineEdge)
        .where(TimelineEdge.source_snapshot_id == child_id)
        .values(source_snapshot_id=snapshot_id)
    )

    # Step 2: Move child's history to parent
    await session.execute(
        update(SnapshotHistory)
        .where(SnapshotHistory.snapshot_id == child_id)
        .values(snapshot_id=snapshot_id)
    )

    # Step 3: Delete parent's current roster
    await session.execute(delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id))

    # Step 4: Move child's roster to parent
    await session.execute(
        update(SnapshotPlayer)
        .where(SnapshotPlayer.snapshot_id == child_id)
        .values(snapshot_id=snapshot_id)
    )

    # Step 5: Delete the branch edge
    await session.execute(delete(TimelineEdge).where(TimelineEdge.id == edge.id))
    await session.execute(delete(GraphNode).where(GraphNode.id == edge.id))

    # Step 6: Delete child snapshot and its graph node
    await session.execute(delete(Snapshot).where(Snapshot.id == child_id))
    await session.execute(delete(GraphNode).where(GraphNode.id == child_id))

    # Step 7: Recursively check if we need to squash again
    await squash_linear_branch(session, snapshot_id)


async def create_game_edge(
    session: AsyncSession,
    source_snapshot_id: int,
    output_snapshot_id: int,
    attempts: int,
    share_text: str,
) -> int:
    """Create a game edge with details."""
    edge_id = await create_timeline_edge(session, "game", source_snapshot_id, output_snapshot_id)

    detail = GameDetail(
        timeline_edge_id=edge_id,
        attempts=attempts,
        share_text=share_text,
    )
    session.add(detail)
    return edge_id


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


async def save_game(
    session: AsyncSession,
    input_snapshot_id: int,
    resultado: DraftResult,
    intentos: int,
    copypaste_text: str,
) -> int:
    """Save a game result to the database."""
    # Create output snapshot
    snap_id = await create_snapshot(session, "organizar")

    # Count cupos jugados per player
    cupos_jugados: Counter[str] = Counter()
    for table in resultado.tables:
        for player in table.players:  # type: ignore
            cupos_jugados[player.name] += 1  # type: ignore

    nombres_en_espera: set[str] = {j.name for j in resultado.waitlist_players}

    for p in await get_snapshot_players(session, input_snapshot_id):
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0

        result = await session.execute(select(Player).where(Player.name == nombre))
        player: Player | None = result.scalar_one_or_none()
        if not player:
            continue

        await add_player_to_snapshot(
            session,
            snap_id,
            player.id,
            "Antiguo" if fue_promovido else p["experiencia"],
            p["juegos_este_ano"] + jugadas,
            1 if nombre in nombres_en_espera else 0,
            p["partidas_deseadas"],
            0,  # partidas_gm reset
        )

    # Create event and details
    edge_id = await create_game_edge(session, input_snapshot_id, snap_id, intentos, copypaste_text)

    # Save mesas
    for table in resultado.tables:
        table_obj = GameTable(timeline_edge_id=edge_id, table_number=table.table_number)
        session.add(table_obj)
        await session.flush()
        table_id = table_obj.id

        # Save GM if present
        if table.gm:
            result = await session.execute(select(Player).where(Player.name == table.gm.name))
            gm_player = result.scalar_one_or_none()
            if gm_player:
                table_obj.gm_player_id = gm_player.id

        # Save players
        for orden, player in enumerate(table.players, 1):  # type: ignore
            result = await session.execute(select(Player).where(Player.name == player.name))  # type: ignore
            db_player = result.scalar_one_or_none()
            if db_player:
                table_player = TablePlayer(
                    table_id=table_id,
                    player_id=db_player.id,
                    seat_order=orden,
                    country=player.country,  # type: ignore
                )
                session.add(table_player)

    # Save waiting list
    for orden, player in enumerate(resultado.waitlist_players, 1):  # type: ignore
        result = await session.execute(select(Player).where(Player.name == player.name))  # type: ignore
        db_player = result.scalar_one_or_none()
        if db_player:
            waiting = WaitingList(
                timeline_edge_id=edge_id,
                player_id=db_player.id,
                list_order=orden,
                missing_spots=int(player.desired_games),  # type: ignore
            )
            session.add(waiting)

    return snap_id


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
            experience=r["experiencia"],
            games_this_year=int(r["juegos_este_ano"]),
            c_england=int(r.get("c_england", 0)),
            c_france=int(r.get("c_france", 0)),
            c_germany=int(r.get("c_germany", 0)),
            c_italy=int(r.get("c_italy", 0)),
            c_austria=int(r.get("c_austria", 0)),
            c_russia=int(r.get("c_russia", 0)),
            c_turkey=int(r.get("c_turkey", 0)),
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
            "last_updated": r.last_updated,
        }
        for r in rows
    ]


# ── Mesa Management ─────────────────────────────────────────────────────────


async def add_table_player(
    session: AsyncSession,
    table_id: int,
    player_id: int,
    seat_order: int,
    country: str,
    country_reason: str | None = None,
) -> None:
    """Add a player to a game table."""
    tp = TablePlayer(
        table_id=table_id,
        player_id=player_id,
        seat_order=seat_order,
        country=country,
        country_reason=country_reason,
    )
    session.add(tp)


async def add_waiting_player(
    session: AsyncSession,
    timeline_edge_id: int,
    player_id: int,
    list_order: int,
    missing_spots: int,
) -> None:
    """Add a player to the waiting list."""
    wl = WaitingList(
        timeline_edge_id=timeline_edge_id,
        player_id=player_id,
        list_order=list_order,
        missing_spots=missing_spots,
    )
    session.add(wl)


async def create_game_table(session: AsyncSession, timeline_edge_id: int, table_number: int) -> int:
    """Create a new game table and return its ID."""
    from sqlalchemy import insert

    stmt = (
        insert(GameTable)
        .values(timeline_edge_id=timeline_edge_id, table_number=table_number)
        .returning(GameTable.id)
    )
    result = await session.execute(stmt)
    await session.flush()
    row = result.scalar_one()
    return row


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
