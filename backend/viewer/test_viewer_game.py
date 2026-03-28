"""
test_viewer_game.py — Tests for /api/game/draft and /api/game/save endpoints.

Tests the two-step Draft Mode:
  POST /api/game/draft  → generate draft (no DB write)
  POST /api/game/save   → persist confirmed draft
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.db import db

# Fixtures are provided by conftest.py


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_snapshot_with_players(conn: sqlite3.Connection, count: int = 14) -> int:
    """Creates a snapshot with `count` players, enough for the algorithm."""
    snap_id = db.create_snapshot(conn, "manual")
    for i in range(count):
        pid = db.get_or_create_player(conn, f"Jugador_{i:02d}")
        db.add_snapshot_player(conn, snap_id, pid, "Antiguo", i % 3, 0, 2, 0)
    conn.commit()
    return snap_id


# ── POST /api/game/draft ──────────────────────────────────────────────────────

class TestApiGameDraft:
    def test_missing_snapshot_id_returns_400(self, client: tuple[Any, sqlite3.Connection]) -> None:
        c, _ = client
        resp = c.post(
            "/api/game/draft",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "snapshot_id" in resp.get_json()["error"]

    def test_valid_snapshot_returns_draft(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_draft_does_not_write_to_db(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_too_few_players_returns_400(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_draft_response_has_expected_player_shape(self, client: tuple[Any, sqlite3.Connection]) -> None:
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
    def test_missing_draft_returns_400(self, client: tuple[Any, sqlite3.Connection]) -> None:
        c, _ = client
        resp = c.post(
            "/api/game/save",
            data=json.dumps({"snapshot_id": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_snapshot_id_returns_400(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_save_draft_returns_game_id(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_save_draft_creates_game_event_in_db(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_save_draft_persists_correct_mesa_count(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_save_draft_creates_output_snapshot(self, client: tuple[Any, sqlite3.Connection]) -> None:
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

    def test_save_draft_with_editing_game_id_leaf_node(self, client: tuple[Any, sqlite3.Connection]) -> None:
        """Test in-place editing when the game is a leaf node (no children)."""
        c, conn = client
        
        # 1. Setup a game using /api/game/save (makes its output snapshot a leaf node)
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
        original_game_id = save_resp.get_json()["game_id"]
        
        # Verify the game exists and is a leaf node initially
        game_row = conn.execute(
            "SELECT output_snapshot_id FROM events WHERE id = ? AND type = 'game'",
            (original_game_id,)
        ).fetchone()
        assert game_row is not None
        output_snapshot_id = game_row["output_snapshot_id"]
        
        # Verify it's a leaf node (no events source from it)
        is_leaf = conn.execute(
            "SELECT 1 FROM events WHERE source_snapshot_id = ? LIMIT 1",
            (output_snapshot_id,)
        ).fetchone() is None
        assert is_leaf, "Game should be a leaf node initially"
        
        # Count events before update
        events_before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        
        # 2. Send a new POST to /api/game/save including editing_game_id
        modified_draft = draft.copy()
        modified_draft["intentos_usados"] = 999  # Change to distinguish
        
        update_resp = c.post(
            "/api/game/save",
            data=json.dumps({
                "snapshot_id": snap_id, 
                "draft": modified_draft,
                "editing_game_id": original_game_id
            }),
            content_type="application/json",
        )
        
        # 3. Assert that it returns the *same* game_id (proving it updated in-place)
        assert update_resp.status_code == 200
        updated_game_id = update_resp.get_json()["game_id"]
        assert updated_game_id == original_game_id, "Should return same game_id for in-place update"
        
        # Assert that it did not create a new row in the events table
        events_after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert events_after == events_before, "Should not create new event for in-place update"
        
        # Verify the game details were updated (intentos should be 999)
        updated_intentos = conn.execute(
            "SELECT intentos FROM game_details WHERE event_id = ?",
            (original_game_id,)
        ).fetchone()["intentos"]
        assert updated_intentos == 999, "Game details should be updated in-place"

    def test_save_draft_with_editing_game_id_internal_node(self, client: tuple[Any, sqlite3.Connection]) -> None:
        """Test fallback behavior when the game is an internal node (has children)."""
        c, conn = client
        
        # 1. Setup a game
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
        original_game_id = save_resp.get_json()["game_id"]
        
        # Get the output snapshot of the original game
        game_row = conn.execute(
            "SELECT output_snapshot_id FROM events WHERE id = ? AND type = 'game'",
            (original_game_id,)
        ).fetchone()
        assert game_row is not None
        output_snapshot_id = game_row["output_snapshot_id"]
        
        # 2. Create a new manual snapshot originating from that game's output snapshot
        # (this makes the game's output snapshot an internal node with children)
        manual_edits = [
            {"nombre": "Jugador_00", "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 0},
            {"nombre": "Jugador_01", "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0},
        ]
        db.create_manual_snapshot(conn, output_snapshot_id, manual_edits)
        conn.commit()
        
        # Verify the original game is now an internal node (has children)
        is_leaf = conn.execute(
            "SELECT 1 FROM events WHERE source_snapshot_id = ? LIMIT 1",
            (output_snapshot_id,)
        ).fetchone() is None
        assert not is_leaf, "Game should now be an internal node"
        
        # Count events before update
        events_before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        
        # 3. Send a POST to /api/game/save including editing_game_id
        modified_draft = draft.copy()
        modified_draft["intentos_usados"] = 777  # Change to distinguish
        
        update_resp = c.post(
            "/api/game/save",
            data=json.dumps({
                "snapshot_id": snap_id, 
                "draft": modified_draft,
                "editing_game_id": original_game_id
            }),
            content_type="application/json",
        )
        
        # 4. Assert that it falls back to standard behavior: returns a *new* game_id
        assert update_resp.status_code == 200
        new_game_id = update_resp.get_json()["game_id"]
        assert new_game_id != original_game_id, "Should return new game_id for internal node"
        
        # Assert that it creates a new branch in the events table
        events_after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert events_after == events_before + 1, "Should create new event for internal node"
        
        # Verify the new game exists and has the updated intentos
        new_intentos = conn.execute(
            "SELECT intentos FROM game_details WHERE event_id = ?",
            (new_game_id,)
        ).fetchone()["intentos"]
        assert new_intentos == 777, "New game should have updated intentos"
        
        # Verify the original game is unchanged
        original_intentos = conn.execute(
            "SELECT intentos FROM game_details WHERE event_id = ?",
            (original_game_id,)
        ).fetchone()["intentos"]
        assert original_intentos != 777, "Original game should remain unchanged"
