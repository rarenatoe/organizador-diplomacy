"""Player-related CRUD operations.

This module contains database operations for player management,
extracted from the monolithic crud.py file for better organization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    GameTable,
    NotionCache,
    Player,
    SnapshotHistory,
    SnapshotPlayer,
    TablePlayer,
    TimelineEdge,
    WaitingList,
)


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


async def lookup_player_history(
    session: AsyncSession,
    names: list[str],
    snapshot_id: int | None = None,
) -> dict[str, dict[str, int | str]]:
    """
    Walk backward through timeline to find player's historical stats.

    Args:
        session: Database session
        names: List of player names to lookup
        snapshot_id: Starting snapshot ID (uses latest if None)

    Returns:
        Dictionary mapping player names to their stats and source flag
    """
    # Get starting snapshot ID if not provided
    if snapshot_id is None:
        from backend.crud.snapshots import get_latest_snapshot_id

        snapshot_id = await get_latest_snapshot_id(session)

    result: dict[str, dict[str, int | str]] = {}

    for name in names:
        # Walk backward through timeline
        current_snapshot_id = snapshot_id
        found_in_history = False
        player = None  # Initialize player variable

        while current_snapshot_id is not None and not found_in_history:
            # Check if player exists in current snapshot
            player_result = await session.execute(select(Player).where(Player.name == name))
            player = player_result.scalar_one_or_none()

            if player:
                # Check if player is linked to this snapshot
                snapshot_player_result = await session.execute(
                    select(SnapshotPlayer).where(
                        SnapshotPlayer.snapshot_id == current_snapshot_id,
                        SnapshotPlayer.player_id == player.id,
                    )
                )
                snapshot_player = snapshot_player_result.scalar_one_or_none()

                if snapshot_player:
                    # Found player in history
                    result[name] = {
                        "prioridad": snapshot_player.priority,
                        "experiencia": snapshot_player.experience,
                        "juegos_este_ano": snapshot_player.games_this_year,
                        "partidas_deseadas": snapshot_player.desired_games,
                        "partidas_gm": snapshot_player.gm_games,
                        "source": "history",
                    }
                    found_in_history = True
                    break

            # Move to previous snapshot via timeline edge
            edge_result = await session.execute(
                select(TimelineEdge).where(TimelineEdge.output_snapshot_id == current_snapshot_id)
            )
            edge = edge_result.scalar_one_or_none()
            current_snapshot_id = edge.source_snapshot_id if edge else None

        # Fallback 1: Global Search against SnapshotPlayer table
        if not found_in_history and player:
            global_search_result = await session.execute(
                select(SnapshotPlayer)
                .where(SnapshotPlayer.player_id == player.id)
                .order_by(SnapshotPlayer.snapshot_id.desc())
                .limit(1)
            )
            global_snapshot_player = global_search_result.scalar_one_or_none()

            if global_snapshot_player:
                # Found in global search
                result[name] = {
                    "prioridad": global_snapshot_player.priority,
                    "experiencia": global_snapshot_player.experience,
                    "juegos_este_ano": global_snapshot_player.games_this_year,
                    "partidas_deseadas": global_snapshot_player.desired_games,
                    "partidas_gm": global_snapshot_player.gm_games,
                    "source": "history",
                }
                found_in_history = True

        # Fallback 2: JSON Logs Search in SnapshotHistory
        if not found_in_history:
            history_logs_result = await session.execute(
                select(SnapshotHistory).order_by(SnapshotHistory.id.desc()).limit(50)
            )
            history_logs = history_logs_result.scalars().all()

            for history_log in history_logs:
                if history_log.previous_state and "players" in history_log.previous_state:
                    players_in_log = history_log.previous_state["players"]
                    for logged_player in players_in_log:
                        if logged_player.get("nombre") == name:
                            # Found in JSON logs - TypedDict provides type safety
                            player_data: dict[str, int | str] = {
                                "prioridad": logged_player.get("prioridad", 0),
                                "experiencia": logged_player.get("experiencia", "Nuevo"),
                                "juegos_este_ano": logged_player.get("juegos_este_ano", 0),
                                "partidas_deseadas": logged_player.get("partidas_deseadas", 1),
                                "partidas_gm": logged_player.get("partidas_gm", 0),
                                "source": "history",
                            }
                            result[name] = player_data
                            found_in_history = True
                            break
                if found_in_history:
                    break

        if not found_in_history:
            # Check Notion cache as fallback
            notion_result = await session.execute(
                select(NotionCache).where(NotionCache.name == name)
            )
            notion_player = notion_result.scalar_one_or_none()

            if notion_player:
                # Found in Notion cache, force priority to 0
                result[name] = {
                    "prioridad": 0,
                    "experiencia": notion_player.experience,
                    "juegos_este_ano": notion_player.games_this_year,
                    "partidas_deseadas": 1,
                    "partidas_gm": 0,
                    "source": "notion",
                }
            else:
                # Not found anywhere, return defaults
                result[name] = {
                    "prioridad": 0,
                    "experiencia": "Nuevo",
                    "juegos_este_ano": 0,
                    "partidas_deseadas": 1,
                    "partidas_gm": 0,
                    "source": "default",
                }

    return result
