"""
db.py – SQLite persistence layer.  Single source of truth for schema,
connection management, and all query helpers.

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

  # Sync events
  create_sync_event(conn, source_snapshot_id, output_snapshot_id) → int

  # Game events
  create_game_event(conn, input_snapshot_id, output_snapshot_id,
                    intentos, copypaste_text)          → int
  create_mesa(conn, game_event_id, numero, gm_player_id)         → int
  add_mesa_player(conn, mesa_id, player_id, orden)               → None
  add_waiting_player(conn, game_event_id, player_id,
                     orden, cupos_faltantes)           → None

  # Post-game snapshot (updated player state)
  create_output_snapshot(conn, input_snapshot_id, resultado)     → int

  # Viewer helpers (read-only complex queries — see db_views.py)
  build_chain_data, get_snapshot_detail, get_game_event_detail
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from utils import DIRECTORIO

if TYPE_CHECKING:
    from models import ResultadoPartidas

# ── Paths ──────────────────────────────────────────────────────────────────────

DB_PATH: Path = DIRECTORIO / "diplomacy.db"

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

CREATE TABLE IF NOT EXISTS sync_events (
    id               INTEGER PRIMARY KEY,
    created_at       TEXT    NOT NULL,
    source_snapshot  INTEGER REFERENCES snapshots(id),  -- NULL = first ever sync
    output_snapshot  INTEGER NOT NULL REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS game_events (
    id                 INTEGER PRIMARY KEY,
    created_at         TEXT    NOT NULL,
    input_snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    output_snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    intentos           INTEGER NOT NULL,
    copypaste_text     TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mesas (
    id            INTEGER PRIMARY KEY,
    game_event_id INTEGER NOT NULL REFERENCES game_events(id) ON DELETE CASCADE,
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
    game_event_id   INTEGER NOT NULL REFERENCES game_events(id) ON DELETE CASCADE,
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
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


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


# ── Sync events ────────────────────────────────────────────────────────────────

def create_sync_event(
    conn: sqlite3.Connection,
    source_snapshot_id: int | None,
    output_snapshot_id: int,
) -> int:
    """Inserts a sync_events row. Does NOT commit."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO sync_events (created_at, source_snapshot, output_snapshot)
        VALUES (?, ?, ?)
        """,
        (ts, source_snapshot_id, output_snapshot_id),
    )
    return cur.lastrowid  # type: ignore[return-value]


# ── Game events ────────────────────────────────────────────────────────────────

def create_game_event(
    conn: sqlite3.Connection,
    input_snapshot_id: int,
    output_snapshot_id: int,
    intentos: int,
    copypaste_text: str,
) -> int:
    """Inserts a game_events row. Does NOT commit."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO game_events
            (created_at, input_snapshot_id, output_snapshot_id,
             intentos, copypaste_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ts, input_snapshot_id, output_snapshot_id, intentos, copypaste_text),
    )
    return cur.lastrowid  # type: ignore[return-value]


def create_mesa(
    conn: sqlite3.Connection,
    game_event_id: int,
    numero: int,
    gm_player_id: int | None,
) -> int:
    """Inserts a mesas row. Does NOT commit."""
    cur = conn.execute(
        "INSERT INTO mesas (game_event_id, numero, gm_player_id) VALUES (?, ?, ?)",
        (game_event_id, numero, gm_player_id),
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
    game_event_id: int,
    player_id: int,
    orden: int,
    cupos_faltantes: int,
) -> None:
    """Inserts one waiting_list row. Does NOT commit."""
    conn.execute(
        """
        INSERT INTO waiting_list
            (game_event_id, player_id, orden, cupos_faltantes)
        VALUES (?, ?, ?, ?)
        """,
        (game_event_id, player_id, orden, cupos_faltantes),
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
