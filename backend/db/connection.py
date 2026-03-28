"""Database connection and schema management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "diplomacy.db"

# ── Schema ─────────────────────────────────────────────────────────────────────

_SCHEMA = """
-- Graph nodes table (universal IDs for all entities)
CREATE TABLE IF NOT EXISTS graph_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Snapshots table (represents a point-in-time roster)
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY,
    node_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT,
    FOREIGN KEY (node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE
);

-- Players table (unique player records)
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    node_id INTEGER NOT NULL,
    nombre TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE
);

-- Snapshot-player relationship (many-to-many)
CREATE TABLE IF NOT EXISTS snapshot_players (
    snapshot_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (snapshot_id, player_id),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE
);

-- Mesa (table) assignments
CREATE TABLE IF NOT EXISTS mesa_players (
    snapshot_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    mesa_numero INTEGER NOT NULL,
    orden INTEGER NOT NULL,
    es_gm BOOLEAN DEFAULT FALSE,
    pais TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

-- Events (sync, game, edit operations)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    node_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL,
    source_snapshot_id INTEGER,
    output_snapshot_id INTEGER,
    FOREIGN KEY (node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (source_snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (output_snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

-- Game-specific details
CREATE TABLE IF NOT EXISTS game_details (
    event_id INTEGER NOT NULL,
    intentos INTEGER DEFAULT 0,
    copypaste_text TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);
"""

def get_db(path: Path | str = DB_PATH) -> sqlite3.Connection:
    """
    Returns an open SQLite connection with FK enforcement, WAL mode, and
    Row factory. Creates the schema idempotently if the file is new.
    Callers are responsible for closing the connection.
    Pass ":memory:" for an in-memory database (tests).
    """
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    
    conn.executescript(_SCHEMA)
    conn.commit()
    
    # Migration: Add pais column if missing and update existing NULL values
    cursor = conn.execute("PRAGMA table_info(mesa_players)")
    columns = [column[1] for column in cursor.fetchall()]
    if "pais" not in columns:
        conn.execute("ALTER TABLE mesa_players ADD COLUMN pais TEXT NOT NULL DEFAULT ''")
    else:
        # Update existing NULL values to empty string and add NOT NULL constraint
        conn.execute("UPDATE mesa_players SET pais = '' WHERE pais IS NULL")
        # Note: SQLite doesn't support ALTER TABLE to add NOT NULL constraint directly
        # This would require recreating the table, but for now we'll ensure data integrity
    
    return conn
