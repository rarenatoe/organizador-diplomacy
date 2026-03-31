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
    Event,
    GameDetail,
    GraphNode,
    Mesa,
    MesaPlayer,
    NotionCache,
    Player,
    Snapshot,
    SnapshotPlayer,
    WaitingList,
)

if TYPE_CHECKING:
    from backend.organizador.models import ResultadoPartidas


# ── Players ────────────────────────────────────────────────────────────────────


async def get_or_create_player(session: AsyncSession, nombre: str) -> int:
    """Returns the player id, inserting a new row if the name is unknown."""
    result = await session.execute(select(Player).where(Player.nombre == nombre))
    player = result.scalar_one_or_none()
    if player:
        return player.id

    new_player: Player = Player(nombre=nombre)
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
    result = await session.execute(select(Player).where(Player.nombre == old_name))
    old_player = result.scalar_one_or_none()
    if not old_player:
        return False

    old_id = old_player.id

    # Check if new name already exists
    result = await session.execute(select(Player).where(Player.nombre == new_name))
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

        # Handle mesa_players conflicts
        result = await session.execute(
            select(MesaPlayer.mesa_id).where(MesaPlayer.player_id == new_id)
        )
        new_player_mesas = {row for row in result.scalars().all()}

        if new_player_mesas:
            await session.execute(
                delete(MesaPlayer)
                .where(MesaPlayer.player_id == old_id)
                .where(MesaPlayer.mesa_id.in_(new_player_mesas))
            )

        await session.execute(
            update(MesaPlayer).where(MesaPlayer.player_id == old_id).values(player_id=new_id)
        )

        # Update other references
        await session.execute(
            update(Mesa).where(Mesa.gm_player_id == old_id).values(gm_player_id=new_id)
        )
        await session.execute(
            update(WaitingList).where(WaitingList.player_id == old_id).values(player_id=new_id)
        )

        # Check if old player is orphaned
        result = await session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.player_id == old_id)
        )
        has_snapshot_links = result.scalar_one_or_none() is not None

        result = await session.execute(select(Mesa).where(Mesa.gm_player_id == old_id))
        has_gm_links = result.scalar_one_or_none() is not None

        result = await session.execute(select(MesaPlayer).where(MesaPlayer.player_id == old_id))
        has_mesa_links = result.scalar_one_or_none() is not None

        result = await session.execute(select(WaitingList).where(WaitingList.player_id == old_id))
        has_waiting_links = result.scalar_one_or_none() is not None

        if not any([has_snapshot_links, has_gm_links, has_mesa_links, has_waiting_links]):
            await session.execute(delete(Player).where(Player.id == old_id))

        return True
    else:
        # Simple rename
        old_player.nombre = new_name
        return True


async def add_player_to_snapshot(
    session: AsyncSession,
    snapshot_id: int,
    player_id: int,
    experiencia: str,
    juegos_este_ano: int,
    prioridad: int,
    partidas_deseadas: int,
    partidas_gm: int,
) -> None:
    """Link a player to a snapshot with game data."""
    sp = SnapshotPlayer(
        snapshot_id=snapshot_id,
        player_id=player_id,
        experiencia=experiencia,
        juegos_este_ano=juegos_este_ano,
        prioridad=prioridad,
        partidas_deseadas=partidas_deseadas,
        partidas_gm=partidas_gm,
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
        player.nombre: {
            "experiencia": sp.experiencia,
            "juegos_este_ano": sp.juegos_este_ano,
            "prioridad": sp.prioridad,
            "partidas_deseadas": sp.partidas_deseadas,
            "partidas_gm": sp.partidas_gm,
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
    result = await session.execute(
        select(SnapshotPlayer, Player, NotionCache)
        .join(Player)
        .outerjoin(NotionCache, Player.nombre == NotionCache.nombre)
        .where(SnapshotPlayer.snapshot_id == snapshot_id)
        .order_by(SnapshotPlayer.prioridad.desc(), Player.nombre)
    )
    rows = result.all()

    return [
        {
            "nombre": player.nombre,
            "experiencia": sp.experiencia,
            "juegos_este_ano": sp.juegos_este_ano,
            "prioridad": sp.prioridad,
            "partidas_deseadas": sp.partidas_deseadas,
            "partidas_gm": sp.partidas_gm,
            "c_england": cache.c_england if cache else 0,
            "c_france": cache.c_france if cache else 0,
            "c_germany": cache.c_germany if cache else 0,
            "c_italy": cache.c_italy if cache else 0,
            "c_austria": cache.c_austria if cache else 0,
            "c_russia": cache.c_russia if cache else 0,
            "c_turkey": cache.c_turkey if cache else 0,
        }
        for sp, player, cache in rows
    ]


# ── Events ───────────────────────────────────────────────────────────────────


async def create_event(
    session: AsyncSession,
    event_type: str,
    source_snapshot_id: int | None,
    output_snapshot_id: int,
) -> int:
    """Create a new event and return its ID."""
    # Create graph node
    node = GraphNode(entity_type="event")
    session.add(node)
    await session.flush()
    node_id = node.id

    # Create event
    event = Event(
        id=node_id,
        type=event_type,
        source_snapshot_id=source_snapshot_id,
        output_snapshot_id=output_snapshot_id,
    )
    session.add(event)
    await session.flush()
    return event.id


async def create_sync_event(
    session: AsyncSession, source_snapshot_id: int, output_snapshot_id: int
) -> int:
    """Create a sync event."""
    return await create_event(session, "sync", source_snapshot_id, output_snapshot_id)


async def create_game_event(
    session: AsyncSession,
    source_snapshot_id: int,
    output_snapshot_id: int,
    intentos: int,
    copypaste_text: str,
) -> int:
    """Create a game event with details."""
    event_id = await create_event(session, "game", source_snapshot_id, output_snapshot_id)

    detail = GameDetail(
        event_id=event_id,
        intentos=intentos,
        copypaste_text=copypaste_text,
    )
    session.add(detail)
    return event_id


async def delete_snapshot_cascade(session: AsyncSession, snapshot_id: int) -> bool:
    """Delete a snapshot and all its dependent data."""
    # Delete snapshot players
    await session.execute(delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id))

    # Delete events that source from this snapshot
    result = await session.execute(select(Event).where(Event.source_snapshot_id == snapshot_id))
    events = result.scalars().all()

    for event in events:
        # Delete event details
        await session.execute(delete(GameDetail).where(GameDetail.event_id == event.id))

        # Delete mesas
        result = await session.execute(select(Mesa).where(Mesa.event_id == event.id))
        mesas = result.scalars().all()

        for mesa in mesas:
            # Delete mesa players
            await session.execute(delete(MesaPlayer).where(MesaPlayer.mesa_id == mesa.id))

        await session.execute(delete(Mesa).where(Mesa.event_id == event.id))

        # Delete waiting list
        await session.execute(delete(WaitingList).where(WaitingList.event_id == event.id))

        # Delete the event itself
        await session.execute(delete(Event).where(Event.id == event.id))

        # Delete graph node
        await session.execute(delete(GraphNode).where(GraphNode.id == event.id))

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

        result = await session.execute(select(Player).where(Player.nombre == nombre))
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
    await create_event(session, "manual", source_snapshot_id, snap_id)
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
    resultado: ResultadoPartidas,
    intentos: int,
    copypaste_text: str,
) -> int:
    """Save a game result to the database."""
    # Create output snapshot
    snap_id = await create_snapshot(session, "organizar")

    # Count cupos jugados per player
    cupos_jugados: Counter[str] = Counter()
    for mesa in resultado.mesas:
        for jugador in mesa.jugadores:
            cupos_jugados[jugador.nombre] += 1

    nombres_en_espera: set[str] = {j.nombre for j in resultado.tickets_sobrantes}

    for p in await get_snapshot_players(session, input_snapshot_id):
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0

        result = await session.execute(select(Player).where(Player.nombre == nombre))
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
    event_id = await create_game_event(
        session, input_snapshot_id, snap_id, intentos, copypaste_text
    )

    # Save mesas
    for mesa in resultado.mesas:
        mesa_obj = Mesa(event_id=event_id, numero=mesa.numero)
        session.add(mesa_obj)
        await session.flush()
        mesa_id = mesa_obj.id

        # Save GM if present
        if mesa.gm:
            result = await session.execute(select(Player).where(Player.nombre == mesa.gm.nombre))
            gm_player = result.scalar_one_or_none()
            if gm_player:
                mesa_obj.gm_player_id = gm_player.id

        # Save players
        for orden, jugador in enumerate(mesa.jugadores, 1):
            result = await session.execute(select(Player).where(Player.nombre == jugador.nombre))
            player = result.scalar_one_or_none()
            if player:
                mesa_player = MesaPlayer(
                    mesa_id=mesa_id,
                    player_id=player.id,
                    orden=orden,
                    pais=jugador.pais,
                )
                session.add(mesa_player)

    # Save waiting list
    for orden, jugador in enumerate(resultado.tickets_sobrantes, 1):
        result = await session.execute(select(Player).where(Player.nombre == jugador.nombre))
        player = result.scalar_one_or_none()
        if player:
            waiting = WaitingList(
                event_id=event_id,
                player_id=player.id,
                orden=orden,
                cupos_faltantes=int(jugador.partidas_deseadas),
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
            nombre=r["nombre"],
            experiencia=r["experiencia"],
            juegos_este_ano=int(r["juegos_este_ano"]),
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
    result = await session.execute(select(NotionCache).order_by(NotionCache.nombre))
    rows = result.scalars().all()

    return [
        {
            "notion_id": r.notion_id,
            "nombre": r.nombre,
            "experiencia": r.experiencia,
            "juegos_este_ano": r.juegos_este_ano,
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


async def add_mesa_player(
    session: AsyncSession,
    mesa_id: int,
    player_id: int,
    orden: int,
    pais: str,
    pais_reason: str | None = None,
) -> None:
    """Add a player to a mesa."""
    mp = MesaPlayer(
        mesa_id=mesa_id,
        player_id=player_id,
        orden=orden,
        pais=pais,
        pais_reason=pais_reason,
    )
    session.add(mp)


async def add_waiting_player(
    session: AsyncSession,
    event_id: int,
    player_id: int,
    orden: int,
    cupos_faltantes: int,
) -> None:
    """Add a player to the waiting list."""
    wl = WaitingList(
        event_id=event_id,
        player_id=player_id,
        orden=orden,
        cupos_faltantes=cupos_faltantes,
    )
    session.add(wl)


async def create_mesa(session: AsyncSession, event_id: int, numero: int) -> int:
    """Create a new mesa and return its ID."""
    from sqlalchemy import insert

    stmt = insert(Mesa).values(event_id=event_id, numero=numero).returning(Mesa.id)
    result = await session.execute(stmt)
    await session.flush()
    row = result.scalar_one()
    return row
