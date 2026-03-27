"""Player database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3


def get_or_create_player(conn: sqlite3.Connection, nombre: str) -> int:
    """Returns the player id, inserting a new row if the name is unknown."""
    row = conn.execute(
        "SELECT id FROM players WHERE nombre = ?", (nombre,)
    ).fetchone()
    if row:
        return row["id"]
    
    # Create new player
    node_cur = conn.execute("INSERT INTO graph_nodes (entity_type) VALUES ('player')")
    global_id = node_cur.lastrowid or 0
    cur = conn.execute(
        "INSERT INTO players (id, node_id, nombre) VALUES (?, ?, ?)",
        (global_id, global_id, nombre),
    )
    return cur.lastrowid or 0


def rename_player(conn: sqlite3.Connection, old_name: str, new_name: str) -> bool:
    """Rename a player if the new name is not already taken."""
    # Check if new name exists
    if conn.execute("SELECT 1 FROM players WHERE nombre = ?", (new_name,)).fetchone():
        return False
    
    conn.execute(
        "UPDATE players SET nombre = ? WHERE nombre = ?", (new_name, old_name)
    )
    return True


def add_player_to_snapshot(conn: sqlite3.Connection, snapshot_id: int, player_id: int) -> None:
    """Associate a player with a snapshot."""
    node_cur = conn.execute("INSERT INTO graph_nodes (entity_type) VALUES ('snapshot_player')")
    node_id = node_cur.lastrowid or 0
    conn.execute(
        "INSERT INTO snapshot_players (snapshot_id, player_id, node_id) VALUES (?, ?, ?)",
        (snapshot_id, player_id, node_id),
    )


def get_snapshot_players(conn: sqlite3.Connection, snapshot_id: int) -> list[dict[str, Any]]:
    """Return all players associated with a snapshot."""
    rows = conn.execute(
        """
        SELECT p.id, p.nombre
        FROM players p
        JOIN snapshot_players sp ON p.id = sp.player_id
        WHERE sp.snapshot_id = ?
        ORDER BY p.nombre
        """,
        (snapshot_id,),
    ).fetchall()
    return [dict(row) for row in rows]
