"""
test_utils.py — Shared test utilities for backend tests.

Provides common fixtures and helpers used across test files.
"""
from __future__ import annotations

import pytest

from backend.db import db
from .viewer import app


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_db() -> "db.sqlite3.Connection":
    """Returns an in-memory DB with the full schema."""
    return db.get_db(":memory:")


def _add_snapshot(conn, source: str = "notion_sync", players: int = 5) -> int:
    """Creates a snapshot with `players` dummy players and returns the snapshot id."""
    snap_id = db.create_snapshot(conn, source)
    for i in range(players):
        pid = db.get_or_create_player(conn, f"Jugador_{snap_id}_{i}")
        db.add_snapshot_player(conn, snap_id, pid, "Antiguo", i, 0, 1, 0)
    conn.commit()
    return snap_id


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mem_db():
    conn = _make_db()
    yield conn
    conn.close()


@pytest.fixture
def client(mem_db, monkeypatch):
    """Flask test client with db.get_db() patched to return the in-memory DB.

    A thin proxy that swallows close() lets routes follow their normal
    try/finally cleanup without destroying the shared in-memory connection.
    """
    class _NoClose:
        """Proxy for sqlite3.Connection that ignores close() calls."""
        def __init__(self, conn: "db.sqlite3.Connection") -> None:
            object.__setattr__(self, "_c", conn)
        def __getattr__(self, name: str):  # type: ignore[override]
            return getattr(object.__getattribute__(self, "_c"), name)
        def __setattr__(self, name: str, value: object) -> None:
            setattr(object.__getattribute__(self, "_c"), name, value)
        def close(self) -> None:
            pass  # keep the connection alive for the full test

    monkeypatch.setattr(db, "get_db", lambda path=None: _NoClose(mem_db))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, mem_db