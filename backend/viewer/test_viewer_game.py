"""
test_viewer_game.py — Tests for /api/game/draft and /api/game/save endpoints.

Tests the two-step Draft Mode:
  POST /api/game/draft  → generate draft (no DB write)
  POST /api/game/save   → persist confirmed draft
"""
from __future__ import annotations

import json

from backend.db import db

# Fixtures are provided by conftest.py


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_snapshot_with_players(conn, count: int = 14) -> int:
    """Creates a snapshot with `count` players, enough for the algorithm."""
    snap_id = db.create_snapshot(conn, "manual")
    for i in range(count):
        pid = db.get_or_create_player(conn, f"Jugador_{i:02d}")
        db.add_snapshot_player(conn, snap_id, pid, "Antiguo", i % 3, 0, 2, 0)
    conn.commit()
    return snap_id


# ── POST /api/game/draft ──────────────────────────────────────────────────────

class TestApiGameDraft:
    def test_missing_snapshot_id_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/game/draft",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "snapshot_id" in resp.get_json()["error"]

    def test_valid_snapshot_returns_draft(self, client):
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "mesas" in data
        assert "tickets_sobrantes" in data
        assert "intentos_usados" in data
        assert len(data["mesas"]) >= 1

    def test_draft_does_not_write_to_db(self, client):
        """Calling /api/game/draft must NOT create any events in the DB."""
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        event_count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE type = 'game'"
        ).fetchone()[0]
        assert event_count == 0

    def test_too_few_players_returns_400(self, client):
        c, conn = client
        snap_id = db.create_snapshot(conn, "manual")
        for i in range(3):
            pid = db.get_or_create_player(conn, f"Few_{i}")
            db.add_snapshot_player(conn, snap_id, pid, "Antiguo", 0, 0, 1, 0)
        conn.commit()
        resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_draft_response_has_expected_player_shape(self, client):
        """Each player dict in each mesa has the required keys."""
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        data = resp.get_json()
        first_player = data["mesas"][0]["jugadores"][0]
        for key in ("nombre", "es_nuevo", "juegos_ano", "tiene_prioridad"):
            assert key in first_player, f"Missing key '{key}' in player dict"


# ── POST /api/game/save ───────────────────────────────────────────────────────

class TestApiGameSave:
    def test_missing_draft_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/game/save",
            data=json.dumps({"snapshot_id": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_snapshot_id_returns_400(self, client):
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        draft_resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        draft = draft_resp.get_json()
        resp = c.post(
            "/api/game/save",
            data=json.dumps({"draft": draft}),  # missing snapshot_id
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_draft_returns_game_id(self, client):
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        draft_resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        draft = draft_resp.get_json()
        save_resp = c.post(
            "/api/game/save",
            data=json.dumps({"snapshot_id": snap_id, "draft": draft}),
            content_type="application/json",
        )
        assert save_resp.status_code == 200
        data = save_resp.get_json()
        assert "game_id" in data
        assert isinstance(data["game_id"], int)

    def test_save_draft_creates_game_event_in_db(self, client):
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        draft_resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        draft = draft_resp.get_json()
        save_resp = c.post(
            "/api/game/save",
            data=json.dumps({"snapshot_id": snap_id, "draft": draft}),
            content_type="application/json",
        )
        game_id = save_resp.get_json()["game_id"]
        event = conn.execute(
            "SELECT type FROM events WHERE id = ?", (game_id,)
        ).fetchone()
        assert event is not None
        assert event["type"] == "game"

    def test_save_draft_persists_correct_mesa_count(self, client):
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        draft_resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        draft = draft_resp.get_json()
        save_resp = c.post(
            "/api/game/save",
            data=json.dumps({"snapshot_id": snap_id, "draft": draft}),
            content_type="application/json",
        )
        game_id = save_resp.get_json()["game_id"]
        mesas_in_db = conn.execute(
            "SELECT COUNT(*) FROM mesas WHERE event_id = ?", (game_id,)
        ).fetchone()[0]
        assert mesas_in_db == len(draft["mesas"])

    def test_save_draft_creates_output_snapshot(self, client):
        """Saving a draft must produce a new output snapshot."""
        c, conn = client
        snap_id = _make_snapshot_with_players(conn, 14)
        before = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        draft_resp = c.post(
            "/api/game/draft",
            data=json.dumps({"snapshot_id": snap_id}),
            content_type="application/json",
        )
        draft = draft_resp.get_json()
        c.post(
            "/api/game/save",
            data=json.dumps({"snapshot_id": snap_id, "draft": draft}),
            content_type="application/json",
        )
        after = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        assert after == before + 1
