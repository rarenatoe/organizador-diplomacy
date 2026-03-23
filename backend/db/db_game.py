"""
db_game.py – Game-event persistence helpers.

Handles creation of game_events, mesas, mesa_players, waiting_list,
and the post-game output snapshot (source='organizar').

All write helpers do NOT commit — callers commit after all writes succeed.

Public API
──────────
  create_game_event(conn, input_snapshot_id, output_snapshot_id,
                    intentos, copypaste_text)          → int
  create_mesa(conn, game_event_id, numero, gm_player_id)         → int
  add_mesa_player(conn, mesa_id, player_id, orden)               → None
  add_waiting_player(conn, game_event_id, player_id,
                     orden, cupos_faltantes)           → None
  create_output_snapshot(conn, input_snapshot_id, resultado)     → int
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

from .db import add_snapshot_player, create_snapshot, get_snapshot_players

if TYPE_CHECKING:
    from models import ResultadoPartidas

# ── Game events ────────────────────────────────────────────────────────────────

def create_game_event(
    conn: sqlite3.Connection,
    input_snapshot_id: int,
    output_snapshot_id: int,
    intentos: int,
    copypaste_text: str,
) -> int:
    """Inserts a game event row and its game_details. Does NOT commit."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO events
            (created_at, type, source_snapshot_id, output_snapshot_id)
        VALUES (?, 'game', ?, ?)
        """,
        (ts, input_snapshot_id, output_snapshot_id),
    )
    event_id = cur.lastrowid
    conn.execute(
        """
        INSERT INTO game_details (event_id, intentos, copypaste_text)
        VALUES (?, ?, ?)
        """,
        (event_id, intentos, copypaste_text),
    )
    return event_id  # type: ignore[return-value]


def create_mesa(
    conn: sqlite3.Connection,
    event_id: int,
    numero: int,
    gm_player_id: int | None,
) -> int:
    """Inserts a mesas row. Does NOT commit."""
    cur = conn.execute(
        "INSERT INTO mesas (event_id, numero, gm_player_id) VALUES (?, ?, ?)",
        (event_id, numero, gm_player_id),
    )
    return cur.lastrowid  # type: ignore[return-value]


def add_mesa_player(
    conn: sqlite3.Connection,
    mesa_id: int,
    player_id: int,
    orden: int,
) -> None:
    """Inserts one mesa_players row. Does NOT commit."""
    conn.execute(
        "INSERT INTO mesa_players (mesa_id, player_id, orden) VALUES (?, ?, ?)",
        (mesa_id, player_id, orden),
    )


def add_waiting_player(
    conn: sqlite3.Connection,
    event_id: int,
    player_id: int,
    orden: int,
    cupos_faltantes: int,
) -> None:
    """Inserts one waiting_list row. Does NOT commit."""
    conn.execute(
        """
        INSERT INTO waiting_list
            (event_id, player_id, orden, cupos_faltantes)
        VALUES (?, ?, ?, ?)
        """,
        (event_id, player_id, orden, cupos_faltantes),
    )


# ── Post-game snapshot ─────────────────────────────────────────────────────────

def create_output_snapshot(
    conn: sqlite3.Connection,
    input_snapshot_id: int,
    resultado: ResultadoPartidas,
) -> int:
    """
    Creates the post-game snapshot (source='organizar') by copying all players
    from the input snapshot and applying game results:

      - juegos_este_ano  += tables played as a player (GMing does not count)
      - prioridad         = 1 if left on waiting list, 0 otherwise
      - experiencia       = 'Antiguo' if was Nuevo and played ≥ 1 table
      - partidas_gm       = 0  (reassigned manually each event)
      - partidas_deseadas = unchanged

    Does NOT commit.
    """
    cupos_jugados: Counter[str] = Counter(
        j.nombre for mesa in resultado.mesas for j in mesa.jugadores
    )
    nombres_en_espera: set[str] = {j.nombre for j in resultado.tickets_sobrantes}

    snap_id = create_snapshot(conn, "organizar")

    for p in get_snapshot_players(conn, input_snapshot_id):
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0
        pid = conn.execute(
            "SELECT id FROM players WHERE nombre = ?", (nombre,)
        ).fetchone()["id"]
        add_snapshot_player(
            conn, snap_id, pid,
            "Antiguo" if fue_promovido else p["experiencia"],
            p["juegos_este_ano"] + jugadas,
            1 if nombre in nombres_en_espera else 0,
            p["partidas_deseadas"],
            0,  # partidas_gm reset
        )

    return snap_id
