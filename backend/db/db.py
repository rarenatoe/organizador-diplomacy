"""
DEPRECATED: Legacy synchronous database module stub.

This module exists only for backward compatibility with legacy code.
New code should use the async modules in backend.db.crud instead.

The following legacy modules still depend on this: - backend/sync/notion_sync.py (CLI script)
- backend/organizador/organizador.py (legacy CLI script)
- backend/organizador/persistence.py (legacy sync functions)
- backend/sync/test_cache_daemon.py (legacy tests)
"""
from __future__ import annotations

import sqlite3
from typing import Any

# This stub prevents ImportError but actual functionality should migrate to async

DB_PATH = "data/diplomacy.db"


def get_db(db_path: str = "data/diplomacy.db") -> sqlite3.Connection:
    """
    DEPRECATED: Returns a synchronous SQLite connection.
    Use AsyncSession from backend.db.connection for new code.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_snapshot_players(conn: sqlite3.Connection, snapshot_id: int) -> list[dict[str, Any]]:
    """
    DEPRECATED: Synchronous version for legacy CLI scripts.
    Use crud.get_snapshot_players() with AsyncSession for new code.
    """
    rows = conn.execute(
        """
        SELECT 
            p.id, p.nombre,
            sp.experiencia, sp.juegos_este_ano,
            sp.prioridad, sp.partidas_deseadas, sp.partidas_gm,
            COALESCE(nc.c_england, 0) as c_england,
            COALESCE(nc.c_france, 0) as c_france,
            COALESCE(nc.c_germany, 0) as c_germany,
            COALESCE(nc.c_italy, 0) as c_italy,
            COALESCE(nc.c_austria, 0) as c_austria,
            COALESCE(nc.c_russia, 0) as c_russia,
            COALESCE(nc.c_turkey, 0) as c_turkey
        FROM snapshot_players sp
        JOIN players p ON sp.player_id = p.id
        LEFT JOIN notion_cache nc ON p.nombre = nc.nombre
        WHERE sp.snapshot_id = ?
        ORDER BY p.nombre
        """,
        (snapshot_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_or_create_player(conn: sqlite3.Connection, nombre: str) -> int:
    """
    DEPRECATED: Synchronous version for legacy CLI scripts.
    Use crud.get_or_create_player() with AsyncSession for new code.
    """
    row = conn.execute("SELECT id FROM players WHERE nombre = ?", (nombre,)).fetchone()
    if row:
        return row["id"]
    conn.execute("INSERT INTO players (nombre) VALUES (?)", (nombre,))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def add_player_to_snapshot(
    conn: sqlite3.Connection,
    snapshot_id: int,
    player_id: int,
    experiencia: str,
    juegos_este_ano: int,
    prioridad: int,
    partidas_deseadas: int,
    partidas_gm: int,
) -> None:
    """
    DEPRECATED: Synchronous version for legacy CLI scripts.
    Use crud.add_player_to_snapshot() with AsyncSession for new code.
    """
    conn.execute(
        """
        INSERT INTO snapshot_players 
        (snapshot_id, player_id, experiencia, juegos_este_ano, prioridad, partidas_deseadas, partidas_gm)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (snapshot_id, player_id, experiencia, juegos_este_ano, prioridad, partidas_deseadas, partidas_gm)
    )


def add_snapshot_player(
    conn: sqlite3.Connection,
    snapshot_id: int,
    player_id: int,
    experiencia: str,
    juegos_este_ano: int,
    prioridad: int,
    partidas_deseadas: int,
    partidas_gm: int,
) -> None:
    """
    DEPRECATED: Alias for add_player_to_snapshot. Legacy CLI scripts use both names.
    Use crud.add_player_to_snapshot() with AsyncSession for new code.
    """
    add_player_to_snapshot(conn, snapshot_id, player_id, experiencia, juegos_este_ano, prioridad, partidas_deseadas, partidas_gm)


def create_snapshot(conn: sqlite3.Connection, source: str) -> int:
    """
    DEPRECATED: Synchronous version for legacy CLI scripts.
    Use crud.create_snapshot() with AsyncSession for new code.
    """
    # Create graph node
    conn.execute("INSERT INTO graph_nodes (entity_type) VALUES ('snapshot')")
    node_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Create snapshot
    conn.execute("INSERT INTO snapshots (id, source) VALUES (?, ?)", (node_id, source))
    return node_id


def create_sync_event(
    conn: sqlite3.Connection,
    source_snapshot_id: int | None,
    output_snapshot_id: int,
) -> int:
    """
    DEPRECATED: Synchronous version for legacy CLI scripts.
    Use crud.create_sync_event() with AsyncSession for new code.
    """
    # Create graph node
    conn.execute("INSERT INTO graph_nodes (entity_type) VALUES ('event')")
    event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Create event
    conn.execute(
        "INSERT INTO events (id, type, source_snapshot_id, output_snapshot_id) VALUES (?, 'sync', ?, ?)",
        (event_id, source_snapshot_id, output_snapshot_id)
    )
    return event_id


def snapshots_have_same_roster(
    conn: sqlite3.Connection,
    snapshot_id: int,
    new_players: list[dict[str, Any]],
) -> bool:
    """
    DEPRECATED: Synchronous version for legacy CLI scripts.
    Use crud.snapshots_have_same_roster() with AsyncSession for new code.
    """
    existing = get_snapshot_players(conn, snapshot_id)
    
    # Create normalized sets for comparison (nombre, experiencia, juegos_este_ano)
    existing_set = {
        (r["nombre"], r["experiencia"], r["juegos_este_ano"])
        for r in existing
    }
    new_set = {
        (p["Nombre"], p["Experiencia"], p["Juegos_Este_Ano"])
        for p in new_players
    }
    
    return existing_set == new_set
