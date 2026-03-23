"""
db.py – SQLite persistence layer.  Single source of truth for schema,
connection management, and snapshot/player/sync helpers.

One file: data/diplomacy.db
No CSVs, no .txt reports, no metadata.json.

Public API
──────────
  DB_PATH                   – default Path for the database file
  get_db(path)              – open a connection (creates schema if needed)

  # Players
  get_or_create_player(conn, nombre)                   → int
  get_snapshot_players(conn, snapshot_id)              → list[dict]

  # Snapshots
  create_snapshot(conn, source)                        → int
  add_snapshot_player(conn, snapshot_id, player_id, …) → None
  get_latest_snapshot_id(conn)                         → int | None
  snapshots_have_same_roster(conn, snapshot_id, rows)  → bool

  # Manual snapshot (UI edit)
  create_manual_snapshot(conn, source_snapshot_id, edits) → int

  # Sync events
  create_sync_event(conn, source_snapshot_id, output_snapshot_id) → int

  # Game events / mesas / post-game snapshot — see db_game.py

  # Delete (cascade to events, mesas, waiting_list, snapshot_players)
  delete_snapshot_cascade(conn, snapshot_id)               → list[int]

  # Viewer helpers (read-only complex queries) — see db_views.py
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from backend.config import DATA_DIR

# ── Paths ──────────────────────────────────────────────────────────────────────

DB_PATH: Path = DATA_DIR / "diplomacy.db"

# ── Schema ─────────────────────────────────────────────────────────────────────

_SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS players (
    id     INTEGER PRIMARY KEY,
    nombre TEXT    UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id         INTEGER PRIMARY KEY,
    created_at TEXT    NOT NULL,
    source     TEXT    NOT NULL CHECK(source IN ('notion_sync', 'organizar', 'manual'))
);

CREATE TABLE IF NOT EXISTS snapshot_players (
    snapshot_id       INTEGER NOT NULL REFERENCES snapshots(id)  ON DELETE CASCADE,
    player_id         INTEGER NOT NULL REFERENCES players(id),
    experiencia       TEXT    NOT NULL CHECK(experiencia IN ('Nuevo', 'Antiguo')),
    juegos_este_ano   INTEGER NOT NULL DEFAULT 0,
    prioridad         INTEGER NOT NULL DEFAULT 0,   -- 0/1 boolean
    partidas_deseadas INTEGER NOT NULL DEFAULT 1,
    partidas_gm       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, player_id)
);

CREATE TABLE IF NOT EXISTS events (
    id                 INTEGER PRIMARY KEY,
    created_at         TEXT    NOT NULL,
    type               TEXT    NOT NULL CHECK(type IN ('sync', 'game', 'edit')),
    source_snapshot_id INTEGER REFERENCES snapshots(id),
    output_snapshot_id INTEGER NOT NULL REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS game_details (
    event_id       INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    intentos       INTEGER NOT NULL,
    copypaste_text TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mesas (
    id            INTEGER PRIMARY KEY,
    event_id      INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    numero        INTEGER NOT NULL,
    gm_player_id  INTEGER REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS mesa_players (
    mesa_id   INTEGER NOT NULL REFERENCES mesas(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id),
    orden     INTEGER NOT NULL,     -- seat number within the table (1-based)
    PRIMARY KEY (mesa_id, player_id)
);

CREATE TABLE IF NOT EXISTS waiting_list (
    id              INTEGER PRIMARY KEY,
    event_id        INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    player_id       INTEGER NOT NULL REFERENCES players(id),
    orden           INTEGER NOT NULL,  -- display order
    cupos_faltantes INTEGER NOT NULL
);
"""

# ── Connection ─────────────────────────────────────────────────────────────────

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
    
    # Check if old tables exist and migrate
    _migrate_old_schema(conn)
    
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _migrate_old_schema(conn: sqlite3.Connection) -> None:
    """Migrate data from old sync_events/game_events tables to unified events table."""
    # Check if old tables exist
    old_tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sync_events', 'game_events')"
    ).fetchall()
    
    if not old_tables:
        return  # No old tables, nothing to migrate
    
    # Create new tables if they don't exist yet
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id                 INTEGER PRIMARY KEY,
            created_at         TEXT    NOT NULL,
            type               TEXT    NOT NULL CHECK(type IN ('sync', 'game', 'edit')),
            source_snapshot_id INTEGER REFERENCES snapshots(id),
            output_snapshot_id INTEGER NOT NULL REFERENCES snapshots(id)
        );
        
        CREATE TABLE IF NOT EXISTS game_details (
            event_id       INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
            intentos       INTEGER NOT NULL,
            copypaste_text TEXT    NOT NULL DEFAULT ''
        );
    """)
    
    # Migrate sync_events to events
    try:
        conn.execute("""
            INSERT OR IGNORE INTO events (id, created_at, type, source_snapshot_id, output_snapshot_id)
            SELECT id, created_at, 'sync', source_snapshot, output_snapshot
            FROM sync_events
        """)
    except sqlite3.OperationalError:
        pass  # Table might not exist or columns might be different
    
    # Migrate game_events to events and game_details
    try:
        conn.execute("""
            INSERT OR IGNORE INTO events (id, created_at, type, source_snapshot_id, output_snapshot_id)
            SELECT id, created_at, 'game', input_snapshot_id, output_snapshot_id
            FROM game_events
        """)
        conn.execute("""
            INSERT OR IGNORE INTO game_details (event_id, intentos, copypaste_text)
            SELECT id, intentos, copypaste_text
            FROM game_events
        """)
    except sqlite3.OperationalError:
        pass  # Table might not exist or columns might be different
    
    # Update mesas table to use event_id instead of game_event_id
    try:
        # Check if game_event_id column exists
        cols = conn.execute("PRAGMA table_info(mesas)").fetchall()
        col_names = [c[1] for c in cols]
        if 'game_event_id' in col_names and 'event_id' not in col_names:
            conn.execute("ALTER TABLE mesas RENAME COLUMN game_event_id TO event_id")
    except sqlite3.OperationalError:
        pass
    
    # Update waiting_list table to use event_id instead of game_event_id
    try:
        cols = conn.execute("PRAGMA table_info(waiting_list)").fetchall()
        col_names = [c[1] for c in cols]
        if 'game_event_id' in col_names and 'event_id' not in col_names:
            conn.execute("ALTER TABLE waiting_list RENAME COLUMN game_event_id TO event_id")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()


# ── Players ────────────────────────────────────────────────────────────────────

def get_or_create_player(conn: sqlite3.Connection, nombre: str) -> int:
    """Returns the player id, inserting a new row if the name is unknown."""
    row = conn.execute(
        "SELECT id FROM players WHERE nombre = ?", (nombre,)
    ).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute("INSERT INTO players (nombre) VALUES (?)", (nombre,))
    return cur.lastrowid  # type: ignore[return-value]


def rename_player(conn: sqlite3.Connection, old_name: str, new_name: str) -> bool:
    """
    Renames a player. If new_name already exists in players table, links snapshot_players
    to the existing player and deletes the old player if orphaned.
    Returns True if successful, False if old_name doesn't exist or if new_name is already
    associated with a player in the same snapshot.
    Does NOT commit.
    """
    # Check if old name exists
    old_row = conn.execute(
        "SELECT id FROM players WHERE nombre = ?", (old_name,)
    ).fetchone()
    if not old_row:
        return False
    
    old_id = int(old_row["id"])
    
    # Check if new name already exists
    new_row = conn.execute(
        "SELECT id FROM players WHERE nombre = ?", (new_name,)
    ).fetchone()
    
    if new_row:
        new_id = int(new_row["id"])
        
        # Check if both players are in the same snapshot
        # Get all snapshots where old player appears
        old_snapshots = conn.execute(
            "SELECT DISTINCT snapshot_id FROM snapshot_players WHERE player_id = ?",
            (old_id,)
        ).fetchall()
        
        for snap_row in old_snapshots:
            snapshot_id = int(snap_row["snapshot_id"])
            # Check if new player is also in this snapshot
            new_in_snapshot = conn.execute(
                "SELECT 1 FROM snapshot_players WHERE snapshot_id = ? AND player_id = ?",
                (snapshot_id, new_id)
            ).fetchone()
            
            if new_in_snapshot:
                # New name is already in the same snapshot - block the rename
                return False
        
        # New name exists but not in the same snapshot - link snapshot_players to existing player
        conn.execute(
            "UPDATE snapshot_players SET player_id = ? WHERE player_id = ?",
            (new_id, old_id)
        )
        
        # Check if old player is now orphaned (no snapshots)
        orphan_check = conn.execute(
            "SELECT 1 FROM snapshot_players WHERE player_id = ?",
            (old_id,)
        ).fetchone()
        
        if not orphan_check:
            # Old player is orphaned - delete it
            conn.execute("DELETE FROM players WHERE id = ?", (old_id,))
        
        return True
    else:
        # New name doesn't exist - simple rename
        conn.execute(
            "UPDATE players SET nombre = ? WHERE id = ?",
            (new_name, old_id)
        )
        return True


def add_player_to_snapshot(
    conn: sqlite3.Connection,
    snapshot_id: int,
    nombre: str,
    experiencia: str = "Nuevo",
    juegos_este_ano: int = 0,
    prioridad: int = 0,
    partidas_deseadas: int = 1,
    partidas_gm: int = 0,
) -> int:
    """
    Adds a player to a snapshot. Creates the player if they don't exist.
    Returns the player id. Does NOT commit.
    """
    player_id = get_or_create_player(conn, nombre)
    add_snapshot_player(
        conn, snapshot_id, player_id,
        experiencia, juegos_este_ano,
        prioridad, partidas_deseadas, partidas_gm
    )
    return player_id


def get_snapshot_players(
    conn: sqlite3.Connection, snapshot_id: int
) -> list[dict]:
    """
    Returns all players in a snapshot as a list of dicts, ordered by nombre.
    Each dict has: nombre, experiencia, juegos_este_ano, prioridad,
                   partidas_deseadas, partidas_gm
    """
    rows = conn.execute(
        """
        SELECT p.nombre, sp.experiencia, sp.juegos_este_ano, sp.prioridad,
               sp.partidas_deseadas, sp.partidas_gm
        FROM   snapshot_players sp
        JOIN   players          p  ON p.id = sp.player_id
        WHERE  sp.snapshot_id = ?
        ORDER  BY p.nombre
        """,
        (snapshot_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Snapshots ──────────────────────────────────────────────────────────────────

def create_snapshot(
    conn: sqlite3.Connection,
    source: str,
    created_at: str | None = None,
) -> int:
    """Inserts a new snapshot row. Does NOT commit."""
    ts = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO snapshots (created_at, source) VALUES (?, ?)",
        (ts, source),
    )
    return cur.lastrowid  # type: ignore[return-value]


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
    """Inserts one snapshot_players row. Does NOT commit."""
    conn.execute(
        """
        INSERT INTO snapshot_players
            (snapshot_id, player_id, experiencia, juegos_este_ano,
             prioridad, partidas_deseadas, partidas_gm)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (snapshot_id, player_id, experiencia, juegos_este_ano,
         prioridad, partidas_deseadas, partidas_gm),
    )


def get_latest_snapshot_id(conn: sqlite3.Connection) -> int | None:
    """Returns the id of the most recently created snapshot, or None."""
    row = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()
    val = row[0] if row else None
    return int(val) if val is not None else None


def snapshots_have_same_roster(
    conn: sqlite3.Connection,
    snapshot_id: int,
    notion_rows: list[dict],
) -> bool:
    """
    Returns True if the Notion-fetched rows match the snapshot's data for
    the three fields Notion controls: Nombre, Experiencia, Juegos_Este_Ano.

    If True, notion_sync can skip creating a new snapshot.
    """
    existing = {r["nombre"]: r for r in get_snapshot_players(conn, snapshot_id)}
    notion_names = {r["Nombre"] for r in notion_rows}
    if set(existing) != notion_names:
        return False
    for row in notion_rows:
        ex = existing.get(row["Nombre"])
        if ex is None:
            return False
        if ex["experiencia"] != row["Experiencia"]:
            return False
        if ex["juegos_este_ano"] != int(row["Juegos_Este_Ano"]):
            return False
    return True


# ── Manual snapshot (UI edit) ──────────────────────────────────────────────────

def create_manual_snapshot(
    conn: sqlite3.Connection,
    source_snapshot_id: int,
    edits: list[dict],
) -> int:
    """
    Creates a new 'manual' snapshot based on source_snapshot_id, applying edits.

    `edits` is a list of dicts, one per player to KEEP, with keys:
        nombre            str   (must exist in the source snapshot)
        prioridad         int   (0 or 1)
        partidas_deseadas int
        partidas_gm       int

    Players omitted from `edits` are excluded from the new snapshot.
    Fields not supplied default to the source snapshot value.
    experiencia and juegos_este_ano are always copied unchanged.

    Returns the new snapshot id. Does NOT commit.
    """
    source_players = {
        p["nombre"]: p for p in get_snapshot_players(conn, source_snapshot_id)
    }
    snap_id = create_snapshot(conn, "manual")
    for e in edits:
        nombre = e["nombre"]
        base = source_players.get(nombre)
        if base is None:
            continue  # silently skip unknown names
        pid = conn.execute(
            "SELECT id FROM players WHERE nombre = ?", (nombre,)
        ).fetchone()["id"]
        add_snapshot_player(
            conn, snap_id, pid,
            base["experiencia"],
            base["juegos_este_ano"],
            int(e.get("prioridad",         base["prioridad"])),
            int(e.get("partidas_deseadas", base["partidas_deseadas"])),
            int(e.get("partidas_gm",       base["partidas_gm"])),
        )
    # Insert edit event linking source to new snapshot
    create_event(conn, "edit", source_snapshot_id, snap_id)
    return snap_id


# ── Events (unified) ──────────────────────────────────────────────────────────

def create_event(
    conn: sqlite3.Connection,
    event_type: str,
    source_snapshot_id: int | None,
    output_snapshot_id: int,
    details: dict | None = None,
) -> int:
    """
    Unified event creation helper. Inserts into the events table
    and optionally into game_details if details are provided.

    Args:
        event_type: 'sync', 'game', or 'edit'
        source_snapshot_id: ID of the input/source snapshot (None for first sync)
        output_snapshot_id: ID of the output snapshot
        details: Optional dict with game-specific fields (intentos, copypaste_text)

    Returns the event ID. Does NOT commit.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO events (created_at, type, source_snapshot_id, output_snapshot_id)
        VALUES (?, ?, ?, ?)
        """,
        (ts, event_type, source_snapshot_id, output_snapshot_id),
    )
    event_id = cur.lastrowid

    if details is not None:
        conn.execute(
            """
            INSERT INTO game_details (event_id, intentos, copypaste_text)
            VALUES (?, ?, ?)
            """,
            (event_id, details.get("intentos", 0), details.get("copypaste_text", "")),
        )

    return event_id  # type: ignore[return-value]


def create_sync_event(
    conn: sqlite3.Connection,
    source_snapshot_id: int | None,
    output_snapshot_id: int,
) -> int:
    """Inserts a sync event row. Delegates to create_event. Does NOT commit."""
    return create_event(conn, "sync", source_snapshot_id, output_snapshot_id)


# ── Delete ────────────────────────────────────────────────────────────────────────

def delete_snapshot_cascade(
    conn: sqlite3.Connection,
    snapshot_id: int,
) -> list[int]:
    """
    Deletes a snapshot and all downstream snapshots/events reachable from it
    (DFS over events.source_snapshot_id).
    Also deletes the event that produced snapshot_id (if any).

    Returns the sorted list of snapshot IDs that were deleted.
    Does NOT commit.
    """
    # ── Collect target + all descendants ──────────────────────────────────────
    all_ids: set[int] = {snapshot_id}
    stack = [snapshot_id]
    while stack:
        sid = stack.pop()
        for row in conn.execute(
            "SELECT output_snapshot_id FROM events WHERE source_snapshot_id = ?",
            (sid,),
        ).fetchall():
            out = int(row[0])
            if out not in all_ids:
                all_ids.add(out)
                stack.append(out)

    # ── Delete events that produced each snapshot ────────────────────────────
    # ON DELETE CASCADE handles game_details, mesas, mesa_players, waiting_list
    for sid in all_ids:
        conn.execute("DELETE FROM events WHERE output_snapshot_id = ?", (sid,))

    # ── Delete snapshot players and snapshots ────────────────────────────────
    for sid in all_ids:
        conn.execute("DELETE FROM snapshot_players WHERE snapshot_id = ?", (sid,))
    for sid in all_ids:
        conn.execute("DELETE FROM snapshots WHERE id = ?", (sid,))

    return sorted(all_ids)
