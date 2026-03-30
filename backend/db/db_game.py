"""
DEPRECATED: Legacy game event persistence functions.

This module exists only for backward compatibility with legacy CLI scripts.
New code should use async modules in backend.db.crud instead.

Used by:
- backend/organizador/organizador.py (legacy CLI script)
- backend/organizador/persistence.py (legacy sync functions)
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    from backend.organizador.models import ResultadoPartidas

from backend.db import db


def create_output_snapshot(
    conn: sqlite3.Connection,
    input_snapshot_id: int,
    resultado: ResultadoPartidas,
) -> int:
    """
    DEPRECATED: Creates post-game snapshot based on game results.
    Use async persistence functions in backend.organizador.persistence_async for new code.
    """
    # Count games played per player
    cupos_jugados: Counter[str] = Counter(
        j.nombre for mesa in resultado.mesas for j in mesa.jugadores
    )

    # Track players in waiting list
    nombres_en_espera: set[str] = {j.nombre for j in resultado.tickets_sobrantes}

    # Create new snapshot
    snap_id = db.create_snapshot(conn, "organizar")

    # Copy all players from input snapshot with updated stats
    for p in db.get_snapshot_players(conn, input_snapshot_id):
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0

        pid = conn.execute("SELECT id FROM players WHERE nombre = ?", (nombre,)).fetchone()["id"]

        db.add_snapshot_player(
            conn,
            snap_id,
            pid,
            "Antiguo" if fue_promovido else p["experiencia"],
            p["juegos_este_ano"] + jugadas,
            1 if nombre in nombres_en_espera else 0,  # prioridad
            p["partidas_deseadas"],
            0,  # partidas_gm reset
        )

    return snap_id


def create_game_event(
    conn: sqlite3.Connection,
    source_snapshot_id: int,
    output_snapshot_id: int,
    intentos: int,
    copypaste_text: str,
) -> int:
    """
    DEPRECATED: Creates a game event with details.
    Use crud.create_game_event() with AsyncSession for new code.
    """
    # Create graph node
    conn.execute("INSERT INTO graph_nodes (entity_type) VALUES ('event')")
    event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Create event
    conn.execute(
        """
        INSERT INTO events (id, type, source_snapshot_id, output_snapshot_id)
        VALUES (?, 'game', ?, ?)
        """,
        (event_id, source_snapshot_id, output_snapshot_id),
    )

    # Create game details
    conn.execute(
        """
        INSERT INTO game_details (event_id, intentos, copypaste_text)
        VALUES (?, ?, ?)
        """,
        (event_id, intentos, copypaste_text),
    )

    return event_id


def create_mesa(
    conn: sqlite3.Connection,
    event_id: int,
    numero: int,
    gm_player_id: int | None,
) -> int:
    """
    DEPRECATED: Creates a mesa (game table).
    Use crud.create_mesa() with AsyncSession for new code.
    """
    conn.execute(
        """
        INSERT INTO mesas (event_id, numero, gm_player_id)
        VALUES (?, ?, ?)
        """,
        (event_id, numero, gm_player_id),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def add_mesa_player(
    conn: sqlite3.Connection,
    mesa_id: int,
    player_id: int,
    orden: int,
    pais: str | None = None,
) -> None:
    """
    DEPRECATED: Adds a player to a mesa.
    Use crud.add_mesa_player() with AsyncSession for new code.
    """
    conn.execute(
        """
        INSERT INTO mesa_players (mesa_id, player_id, orden, pais)
        VALUES (?, ?, ?, ?)
        """,
        (mesa_id, player_id, orden, pais or ""),
    )


def add_waiting_player(
    conn: sqlite3.Connection,
    event_id: int,
    player_id: int,
    orden: int,
    cupos_faltantes: int,
) -> None:
    """
    DEPRECATED: Adds a player to the waiting list.
    Use crud.add_waiting_player() with AsyncSession for new code.
    """
    conn.execute(
        """
        INSERT INTO waiting_list (event_id, player_id, orden, cupos_faltantes)
        VALUES (?, ?, ?, ?)
        """,
        (event_id, player_id, orden, cupos_faltantes),
    )
