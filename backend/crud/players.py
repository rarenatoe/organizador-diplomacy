"""Player-related CRUD operations.

This module contains database operations for player management,
extracted from the monolithic crud.py file for better organization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

from sqlalchemy import delete, func, select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.snapshots import HistoryState
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


def normalize_player_name(name: str) -> str:
    """
    Normalize player name by stripping whitespace, collapsing internal spaces,
    and converting to Title Case.

    Args:
        name: Raw player name

    Returns:
        Normalized player name
    """
    # Strip leading/trailing whitespace
    name = name.strip()
    # Collapse multiple internal spaces into single space
    name = " ".join(name.split())
    # Convert to Title Case
    return name.title()


async def get_or_create_player(
    session: AsyncSession, name: str, notion_id: str | None = None
) -> int:
    result = await session.execute(select(Player).where(Player.name == name))
    player = result.scalar_one_or_none()

    if player:
        if notion_id and player.notion_id != notion_id:
            player.notion_id = notion_id
            await session.flush()
        return player.id

    new_player = Player(name=name, notion_id=notion_id)
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

        # Transfer Notion ID if the old player had one and the new player doesn't
        if old_player.notion_id and not new_player.notion_id:
            await session.execute(
                update(Player).where(Player.id == new_id).values(notion_id=old_player.notion_id)
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


SourceType = Literal["history", "notion", "default"]


class PlayerHistoryDict(TypedDict):
    source: SourceType
    is_new: bool
    juegos_este_ano: int
    has_priority: bool
    partidas_deseadas: int
    partidas_gm: int
    notion_id: NotRequired[str]
    notion_name: NotRequired[str]


async def lookup_player_history(
    session: AsyncSession,
    name: str,
    notion_id: str | None = None,
    snapshot_id: int | None = None,
) -> PlayerHistoryDict:
    """
    Walk backward through timeline to find player's historical stats.
    """
    if snapshot_id is None:
        from backend.crud.snapshots import get_latest_snapshot_id

        snapshot_id = await get_latest_snapshot_id(session)

    current_snapshot_id = snapshot_id
    found_in_history = False

    norm_name = normalize_player_name(name)

    player_result = await session.execute(select(Player).where(Player.name == norm_name))
    player = player_result.scalar_one_or_none()

    nc = None
    if notion_id:
        nc_res = await session.execute(
            select(NotionCache).where(NotionCache.notion_id == notion_id)
        )
        nc = nc_res.scalar_one_or_none()
    elif player and player.notion_id:
        nc_res = await session.execute(
            select(NotionCache).where(NotionCache.notion_id == player.notion_id)
        )
        nc = nc_res.scalar_one_or_none()
    else:
        nc_res = await session.execute(
            select(NotionCache).where(func.lower(NotionCache.name) == name.lower())
        )
        nc = nc_res.scalar_one_or_none()

    def build_response(
        source: SourceType,
        played: int,
        desired: int,
        gm: int,
        *,
        has_priority: bool,
        is_new: bool,
    ) -> PlayerHistoryDict:
        # Explicitly declare the type so Pyright knows exactly what this is
        res: PlayerHistoryDict = {
            "source": source,
            "has_priority": has_priority,
            "is_new": is_new,
            "juegos_este_ano": played,
            "partidas_deseadas": desired,
            "partidas_gm": gm,
        }
        # Safely add Notion fields if we found them
        if nc:
            res["notion_id"] = nc.notion_id
            res["notion_name"] = nc.name

        return res

    while current_snapshot_id is not None and not found_in_history:
        if player:
            snapshot_player_result = await session.execute(
                select(SnapshotPlayer).where(
                    SnapshotPlayer.snapshot_id == current_snapshot_id,
                    SnapshotPlayer.player_id == player.id,
                )
            )
            snapshot_player = snapshot_player_result.scalar_one_or_none()

            if snapshot_player:
                return build_response(
                    source="history",
                    played=snapshot_player.games_this_year,
                    desired=snapshot_player.desired_games,
                    gm=snapshot_player.gm_games,
                    has_priority=snapshot_player.has_priority,
                    is_new=snapshot_player.is_new,
                )

        edge_result = await session.execute(
            select(TimelineEdge).where(TimelineEdge.output_snapshot_id == current_snapshot_id)
        )
        edge = edge_result.scalar_one_or_none()
        current_snapshot_id = edge.source_snapshot_id if edge else None

    # Fallback 1: Global Search
    if not found_in_history and player:
        global_search_result = await session.execute(
            select(SnapshotPlayer)
            .where(SnapshotPlayer.player_id == player.id)
            .order_by(SnapshotPlayer.snapshot_id.desc())
            .limit(1)
        )
        global_snapshot_player = global_search_result.scalar_one_or_none()

        if global_snapshot_player:
            return build_response(
                source="history",
                played=global_snapshot_player.games_this_year,
                desired=global_snapshot_player.desired_games,
                gm=global_snapshot_player.gm_games,
                has_priority=global_snapshot_player.has_priority,
                is_new=global_snapshot_player.is_new,
            )

    # Fallback 2: JSON Logs Search
    history_logs_result = await session.execute(
        select(SnapshotHistory).order_by(SnapshotHistory.id.desc()).limit(50)
    )
    history_logs = history_logs_result.scalars().all()

    for history_log in history_logs:
        if history_log.previous_state:
            state = HistoryState.model_validate(history_log.previous_state)

            for logged_player in state.players:
                if logged_player.nombre == name:
                    return build_response(
                        source="history",
                        played=logged_player.juegos_este_ano,
                        desired=logged_player.partidas_deseadas,
                        gm=logged_player.partidas_gm,
                        has_priority=logged_player.has_priority,
                        is_new=logged_player.is_new,
                    )

    # Fallback 3: Check Notion cache
    if nc:
        return build_response(
            source="notion",
            played=nc.games_this_year,
            desired=1,
            gm=0,
            has_priority=False,
            is_new=nc.is_new,
        )

    # Default Backup
    return build_response(
        source="default",
        played=0,
        desired=1,
        gm=0,
        has_priority=False,
        is_new=True,
    )
