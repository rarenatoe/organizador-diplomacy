"""Game-related CRUD operations.

This module contains database operations for game table management,
extracted from the monolithic crud.py file for better organization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import GameTable, TablePlayer, WaitingList


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
    stmt = (
        insert(GameTable)
        .values(timeline_edge_id=timeline_edge_id, table_number=table_number)
        .returning(GameTable.id)
    )
    result = await session.execute(stmt)
    await session.flush()
    row = result.scalar_one()
    return row
