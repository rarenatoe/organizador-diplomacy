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
    Player,
    SnapshotPlayer,
    TablePlayer,
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
