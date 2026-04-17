"""Game-related CRUD operations.

This module contains database operations for game table management,
extracted from the monolithic crud.py file for better organization.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from sqlalchemy import insert, select, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.crud.chain import create_game_edge
from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
    get_snapshot_players,
)
from backend.db.models import GameDetail, GameTable, TablePlayer, WaitingList


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


async def save_game_draft(
    session: AsyncSession, input_snapshot_id: int, draft_data: dict[str, Any]
) -> int:
    """
    Saves a confirmed game draft to the database.
    Returns the new game_event_id.
    """
    # 1. Create the output snapshot
    out_id = await _create_output_snapshot_from_draft(session, input_snapshot_id, draft_data)

    # 2. Create game event with details
    attempts = draft_data.get("intentos_usados", 0)
    event_id = await create_game_edge(session, input_snapshot_id, out_id, attempts)

    # 3. Create tables and table_players
    for table in draft_data.get("mesas", []):
        gm_pid: int | None = None
        gm_nombre = table.get("gm", {}).get("nombre") if table.get("gm") else None
        if gm_nombre:
            gm_pid = await get_or_create_player(session, gm_nombre)

        table_id = await create_game_table(session, event_id, table["numero"])
        if gm_pid:
            # Set GM player
            result = await session.execute(select(GameTable).where(GameTable.id == table_id))
            table_obj = result.scalar_one()
            table_obj.gm_player_id = gm_pid
        for order, player in enumerate(table.get("jugadores", []), start=1):
            pid = await get_or_create_player(session, player["nombre"])
            # Extract country data from the new country object structure
            country_data = player.get("country", {})
            country_name = country_data.get("name", "") if country_data else ""
            country_reason = country_data.get("reason") if country_data else None

            await add_table_player(
                session=session,
                table_id=table_id,
                player_id=pid,
                seat_order=order,
                country=country_name,
                country_reason=country_reason,
            )

    # 5. Create waiting list
    waiting_players = draft_data.get("tickets_sobrantes", [])

    for order, player_dict in enumerate(waiting_players, start=1):
        pid = await get_or_create_player(session, player_dict["nombre"])
        slots = player_dict.get("cupos_faltantes", 1)
        await add_waiting_player(
            session=session,
            timeline_edge_id=event_id,
            player_id=pid,
            list_order=order,
            missing_spots=slots,
        )

    return event_id


async def _create_output_snapshot_from_draft(
    session: AsyncSession, input_snapshot_id: int, draft_data: dict[str, Any]
) -> int:
    """Creates the post-game snapshot based on draft data."""
    slots_played: Counter[str] = Counter()
    for mesa in draft_data.get("mesas", []):
        for j in mesa.get("jugadores", []):
            slots_played[j["nombre"]] += 1

    names_in_waitlist: set[str] = {j["nombre"] for j in draft_data.get("tickets_sobrantes", [])}

    snap_id = await create_snapshot(session, "organizar")

    rows = await get_snapshot_players(session, input_snapshot_id)
    for p in rows:
        name = p["nombre"]
        played = slots_played[name]

        # Get or create player
        pid = await get_or_create_player(session, name)

        await add_player_to_snapshot(
            session=session,
            snapshot_id=snap_id,
            player_id=pid,
            is_new=p["is_new"] and played == 0,
            games_this_year=p["juegos_este_ano"] + played,
            desired_games=p["partidas_deseadas"],
            gm_games=0,  # partidas_gm reset
            has_priority=name in names_in_waitlist,
        )

    return snap_id


async def update_game_draft(
    session: AsyncSession,
    game_id: int,
    input_snapshot_id: int,
    output_snapshot_id: int,
    draft_data: dict[str, Any],
) -> int:
    """
    Updates an existing game draft in place.
    Returns the game_id.
    """

    # 1. Update game_details in place
    attempts = draft_data.get("intentos_usados", 0)

    # Update GameDetail
    result = await session.execute(select(GameDetail).where(GameDetail.timeline_edge_id == game_id))
    gd = result.scalar_one_or_none()
    if gd:
        gd.attempts = attempts

    # 2. Delete existing game_tables and waiting_list for this game
    # Use raw SQL for delete operations
    await session.execute(
        text(
            "DELETE FROM table_players WHERE table_id IN (SELECT id FROM game_tables WHERE timeline_edge_id = :timeline_edge_id)"
        ),
        {"timeline_edge_id": game_id},
    )
    await session.execute(
        text("DELETE FROM game_tables WHERE timeline_edge_id = :timeline_edge_id"),
        {"timeline_edge_id": game_id},
    )
    await session.execute(
        text("DELETE FROM waiting_list WHERE timeline_edge_id = :timeline_edge_id"),
        {"timeline_edge_id": game_id},
    )

    # 3. Delete output snapshot roster and re-insert
    await session.execute(
        text("DELETE FROM snapshot_players WHERE snapshot_id = :snapshot_id"),
        {"snapshot_id": output_snapshot_id},
    )

    # Re-create the output snapshot with updated player data
    slots_played: Counter[str] = Counter()
    for table in draft_data.get("mesas", []):
        for j in table.get("jugadores", []):
            slots_played[j["nombre"]] += 1

    names_in_waitlist: set[str] = {j["nombre"] for j in draft_data.get("tickets_sobrantes", [])}

    rows = await get_snapshot_players(session, input_snapshot_id)
    for p in rows:
        name = p["nombre"]
        played = slots_played[name]
        pid = await get_or_create_player(session, name)

        await add_player_to_snapshot(
            session=session,
            snapshot_id=output_snapshot_id,
            player_id=pid,
            is_new=p["is_new"] and played == 0,
            games_this_year=p["juegos_este_ano"] + played,
            desired_games=p["partidas_deseadas"],
            gm_games=0,  # partidas_gm reset
            has_priority=name in names_in_waitlist,
        )

    # 4. Re-insert tables and waiting_list
    for table in draft_data.get("mesas", []):
        gm_pid: int | None = None
        gm_nombre = table.get("gm", {}).get("nombre") if table.get("gm") else None
        if gm_nombre:
            gm_pid = await get_or_create_player(session, gm_nombre)

        table_id = await create_game_table(session, game_id, table["numero"])
        if gm_pid:
            # Set GM player
            result = await session.execute(select(GameTable).where(GameTable.id == table_id))
            table_obj = result.scalar_one()
            table_obj.gm_player_id = gm_pid
        for order, player in enumerate(table.get("jugadores", []), start=1):
            pid = await get_or_create_player(session, player["nombre"])
            # Extract country data from the new country object structure
            country_data = player.get("country", {})
            country_name = country_data.get("name", "") if country_data else ""
            country_reason = country_data.get("reason") if country_data else None

            await add_table_player(
                session=session,
                table_id=table_id,
                player_id=pid,
                seat_order=order,
                country=country_name,
                country_reason=country_reason,
            )

    # 5. Create waiting list
    waiting_players = draft_data.get("tickets_sobrantes", [])

    for order, player_dict in enumerate(waiting_players, start=1):
        pid = await get_or_create_player(session, player_dict["nombre"])
        slots = player_dict.get("cupos_faltantes", 1)
        await add_waiting_player(
            session=session,
            timeline_edge_id=game_id,
            player_id=pid,
            list_order=order,
            missing_spots=slots,
        )

    return game_id
