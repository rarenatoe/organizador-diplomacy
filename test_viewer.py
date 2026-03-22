"""
test_viewer.py — Unit tests for viewer.py (Flask backend).

Covers:
  - API routes: /api/chain, /api/snapshot/<id>, /api/game/<id>, /api/snapshots
  - /api/run validation (unknown script, invalid snapshot value)
  - db.build_chain_data: tree {"roots": [...]} from DB
"""
from __future__ import annotations

import json

import pytest

import db
import viewer
from viewer import app


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
    """Flask test client with db.get_db() patched to return the in-memory DB."""
    monkeypatch.setattr(db, "get_db", lambda path=None: mem_db)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, mem_db


# ── /api/chain ────────────────────────────────────────────────────────────────

class TestApiChain:
    def test_empty_db_returns_empty_roots(self, client):
        c, conn = client
        resp = c.get("/api/chain")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["roots"] == []

    def test_single_snapshot_is_root(self, client):
        c, conn = client
        _add_snapshot(conn, players=3)
        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["type"] == "snapshot"
        assert root["player_count"] == 3
        assert root["branches"] == []

    def test_sync_branch_not_a_root(self, client):
        """Snapshot produced by a sync_event must be a branch, not a root."""
        c, conn = client
        snap1 = _add_snapshot(conn)
        snap2 = _add_snapshot(conn)
        db.create_sync_event(conn, snap1, snap2)
        conn.commit()
        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["id"] == snap1
        assert len(root["branches"]) == 1
        branch = root["branches"][0]
        assert branch["edge"]["type"] == "sync"
        assert branch["output"]["id"] == snap2

    def test_latest_flag_on_highest_id(self, client):
        """is_latest is True only on the snapshot with the highest id."""
        c, conn = client
        snap1 = _add_snapshot(conn)
        snap2 = _add_snapshot(conn)
        db.create_sync_event(conn, snap1, snap2)
        conn.commit()
        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        root = data["roots"][0]
        assert root["is_latest"] is False
        assert root["branches"][0]["output"]["is_latest"] is True

    def test_two_branches_from_same_snapshot(self, client):
        """
        Regression: two game_events reading from snap1 must produce two sibling
        branches of snap1, not a chain snap1→game_A→snap2→game_B→snap3.
        """
        c, conn = client
        snap1 = _add_snapshot(conn, players=14)
        snap2 = _add_snapshot(conn, source="organizar", players=14)
        snap3 = _add_snapshot(conn, source="organizar", players=14)

        db.create_game_event(conn, snap1, snap2, 1, "copypaste1")
        db.create_game_event(conn, snap1, snap3, 1, "copypaste2")
        conn.commit()

        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        # snap1 is the only root; snap2 and snap3 are children
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["id"] == snap1
        assert len(root["branches"]) == 2
        output_ids = {b["output"]["id"] for b in root["branches"]}
        assert output_ids == {snap2, snap3}


# ── /api/snapshot/<id> ────────────────────────────────────────────────────────

class TestApiSnapshot:
    def test_returns_snapshot_detail(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn, players=4)
        resp = c.get(f"/api/snapshot/{snap_id}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["id"] == snap_id
        assert len(data["players"]) == 4

    def test_unknown_id_returns_404(self, client):
        c, conn = client
        resp = c.get("/api/snapshot/9999")
        assert resp.status_code == 404


# ── /api/game/<id> ────────────────────────────────────────────────────────────

class TestApiGame:
    def test_returns_game_detail(self, client):
        c, conn = client
        snap_in = _add_snapshot(conn, players=7)
        snap_out = _add_snapshot(conn, source="organizar", players=7)
        ge_id = db.create_game_event(conn, snap_in, snap_out, 1, "copypaste text")
        conn.commit()
        resp = c.get(f"/api/game/{ge_id}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["id"] == ge_id
        assert data["copypaste"] == "copypaste text"

    def test_unknown_id_returns_404(self, client):
        c, conn = client
        resp = c.get("/api/game/9999")
        assert resp.status_code == 404


# ── /api/snapshots ────────────────────────────────────────────────────────────

class TestApiSnapshots:
    def test_lists_snapshots_in_order(self, client):
        c, conn = client
        snap1 = _add_snapshot(conn, source="notion_sync")
        snap2 = _add_snapshot(conn, source="organizar")
        resp = c.get("/api/snapshots")
        data = json.loads(resp.data)
        ids = [s["id"] for s in data["snapshots"]]
        assert ids == [snap1, snap2]

    def test_empty_when_no_snapshots(self, client):
        c, conn = client
        resp = c.get("/api/snapshots")
        data = json.loads(resp.data)
        assert data["snapshots"] == []


# ── /api/run ──────────────────────────────────────────────────────────────────

class TestApiRun:
    def test_unknown_script_returns_400(self, client):
        c, conn = client
        resp = c.post("/api/run/evil_script")
        assert resp.status_code == 400

    def test_invalid_snapshot_type_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/run/organizar",
            data=json.dumps({"snapshot": "not_an_int"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_valid_integer_snapshot_accepted(self, client, monkeypatch):
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post(
            "/api/run/organizar",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_no_snapshot_key_accepted(self, client, monkeypatch):
        """Omitting snapshot uses latest — should not 400."""
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post("/api/run/organizar", content_type="application/json")
        assert resp.status_code == 200
