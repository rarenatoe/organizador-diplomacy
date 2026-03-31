"""Async persistence functions for game operations."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.db.crud import (
    add_mesa_player,
    add_player_to_snapshot,
    add_waiting_player,
    create_game_event,
    create_mesa,
    create_snapshot,
    get_or_create_player,
    get_snapshot_players,
)
from backend.db.models import GameDetail, Mesa
from backend.organizador.formatter import formatear_copypaste_from_dict


async def save_game_draft_async(
    session: AsyncSession, input_snapshot_id: int, draft_data: dict[str, Any]
) -> int:
    """
    Async version: Saves a confirmed game draft to the database.
    Returns the new game_event_id.
    """
    # 1. Create the output snapshot
    out_id = await _create_output_snapshot_from_draft_async(session, input_snapshot_id, draft_data)

    # 2. Format copypaste text
    copypaste = formatear_copypaste_from_dict(draft_data)

    # 3. Create the game event with details
    intentos = draft_data.get("intentos_usados", 0)
    event_id = await create_game_event(session, input_snapshot_id, out_id, intentos, copypaste)

    # 4. Create mesas and mesa_players
    for mesa in draft_data.get("mesas", []):
        gm_pid: int | None = None
        gm_nombre = mesa.get("gm", {}).get("nombre") if mesa.get("gm") else None
        if gm_nombre:
            gm_pid = await get_or_create_player(session, gm_nombre)

        mesa_id = await create_mesa(session, event_id, mesa["numero"])
        if gm_pid:
            # Set GM player
            result = await session.execute(select(Mesa).where(Mesa.id == mesa_id))
            mesa_obj = result.scalar_one()
            mesa_obj.gm_player_id = gm_pid
        for orden, jugador in enumerate(mesa.get("jugadores", []), start=1):
            pid = await get_or_create_player(session, jugador["nombre"])
            await add_mesa_player(
                session,
                mesa_id,
                pid,
                orden,
                jugador.get("pais", ""),
                jugador.get("pais_reason"),
            )

    # 5. Create waiting list
    waiting_players = draft_data.get("tickets_sobrantes", [])
    conteo_espera: Counter[str] = Counter(j["nombre"] for j in waiting_players)

    for orden, (nombre, cupos) in enumerate(conteo_espera.items(), start=1):
        pid = await get_or_create_player(session, nombre)
        await add_waiting_player(session, event_id, pid, orden, cupos)

    return event_id


async def _create_output_snapshot_from_draft_async(
    session: AsyncSession, input_snapshot_id: int, draft_data: dict[str, Any]
) -> int:
    """Async version: Creates the post-game snapshot based on draft data."""
    cupos_jugados: Counter[str] = Counter()
    for mesa in draft_data.get("mesas", []):
        for j in mesa.get("jugadores", []):
            cupos_jugados[j["nombre"]] += 1

    nombres_en_espera: set[str] = {j["nombre"] for j in draft_data.get("tickets_sobrantes", [])}

    snap_id = await create_snapshot(session, "organizar")

    rows = await get_snapshot_players(session, input_snapshot_id)
    for p in rows:
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0

        # Get or create player
        pid = await get_or_create_player(session, nombre)

        await add_player_to_snapshot(
            session,
            snap_id,
            pid,
            "Antiguo" if fue_promovido else p["experiencia"],
            p["juegos_este_ano"] + jugadas,
            1 if nombre in nombres_en_espera else 0,
            p["partidas_deseadas"],
            0,  # partidas_gm reset
        )

    return snap_id


async def update_game_draft_async(
    session: AsyncSession,
    game_id: int,
    input_snapshot_id: int,
    output_snapshot_id: int,
    draft_data: dict[str, Any],
) -> int:
    """
    Async version: Updates an existing game draft in place.
    Returns the game_id.
    """

    # 1. Update game_details in place
    copypaste = formatear_copypaste_from_dict(draft_data)
    intentos = draft_data.get("intentos_usados", 0)

    # Update GameDetail
    result = await session.execute(select(GameDetail).where(GameDetail.event_id == game_id))
    gd = result.scalar_one_or_none()
    if gd:
        gd.intentos = intentos
        gd.copypaste_text = copypaste

    # 2. Delete existing mesas and waiting_list for this game
    # Use raw SQL for delete operations
    await session.execute(
        text(
            "DELETE FROM mesa_players WHERE mesa_id IN (SELECT id FROM mesas WHERE event_id = :event_id)"
        ),
        {"event_id": game_id},
    )
    await session.execute(
        text("DELETE FROM mesas WHERE event_id = :event_id"), {"event_id": game_id}
    )
    await session.execute(
        text("DELETE FROM waiting_list WHERE event_id = :event_id"), {"event_id": game_id}
    )

    # 3. Delete output snapshot roster and re-insert
    await session.execute(
        text("DELETE FROM snapshot_players WHERE snapshot_id = :snapshot_id"),
        {"snapshot_id": output_snapshot_id},
    )

    # Re-create the output snapshot with updated player data
    cupos_jugados: Counter[str] = Counter()
    for mesa in draft_data.get("mesas", []):
        for j in mesa.get("jugadores", []):
            cupos_jugados[j["nombre"]] += 1

    nombres_en_espera: set[str] = {j["nombre"] for j in draft_data.get("tickets_sobrantes", [])}

    rows = await get_snapshot_players(session, input_snapshot_id)
    for p in rows:
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0
        pid = await get_or_create_player(session, nombre)

        await add_player_to_snapshot(
            session,
            output_snapshot_id,
            pid,
            "Antiguo" if fue_promovido else p["experiencia"],
            p["juegos_este_ano"] + jugadas,
            1 if nombre in nombres_en_espera else 0,
            p["partidas_deseadas"],
            0,  # partidas_gm reset
        )

    # 4. Re-insert mesas and waiting_list
    for mesa in draft_data.get("mesas", []):
        gm_pid: int | None = None
        gm_nombre = mesa.get("gm", {}).get("nombre") if mesa.get("gm") else None
        if gm_nombre:
            gm_pid = await get_or_create_player(session, gm_nombre)

        mesa_id = await create_mesa(session, game_id, mesa["numero"])
        if gm_pid:
            # Set GM player
            result = await session.execute(select(Mesa).where(Mesa.id == mesa_id))
            mesa_obj = result.scalar_one()
            mesa_obj.gm_player_id = gm_pid
        for orden, jugador in enumerate(mesa.get("jugadores", []), start=1):
            pid = await get_or_create_player(session, jugador["nombre"])
            await add_mesa_player(
                session,
                mesa_id,
                pid,
                orden,
                jugador.get("pais", ""),
                jugador.get("pais_reason"),
            )

    # 5. Create waiting list
    waiting_players = draft_data.get("tickets_sobrantes", [])
    conteo_espera: Counter[str] = Counter(j["nombre"] for j in waiting_players)

    for orden, (nombre, cupos) in enumerate(conteo_espera.items(), start=1):
        pid = await get_or_create_player(session, nombre)
        await add_waiting_player(session, game_id, pid, orden, cupos)

    return game_id
