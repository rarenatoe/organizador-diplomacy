"""
test_viewer_player.py — Tests for /api/player endpoints.

Tests player rename and add player functionality.
"""
from __future__ import annotations

import json

import pytest

from . import db
from .conftest import _add_snapshot


# ── /api/player/rename ────────────────────────────────────────────────────────

class TestApiPlayerRename:
    def test_rename_player_success(self, client):
        c, conn = client
        # Create a player
        pid = db.get_or_create_player(conn, "Turk")
        conn.commit()
        
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Turk", "new_name": "Kurt"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        
        # Verify the name was changed
        row = conn.execute("SELECT nombre FROM players WHERE id = ?", (pid,)).fetchone()
        assert row["nombre"] == "Kurt"

    def test_rename_player_not_found_returns_404(self, client):
        c, conn = client
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "NonExistent", "new_name": "NewName"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_rename_player_new_name_in_same_snapshot_returns_404(self, client):
        c, conn = client
        # Create two players in the same snapshot
        snap_id = db.create_snapshot(conn, "notion_sync")
        pid1 = db.get_or_create_player(conn, "Player1")
        pid2 = db.get_or_create_player(conn, "Player2")
        db.add_snapshot_player(conn, snap_id, pid1, "Antiguo", 0, 0, 1, 0)
        db.add_snapshot_player(conn, snap_id, pid2, "Antiguo", 0, 0, 1, 0)
        conn.commit()

        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Player1", "new_name": "Player2"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_rename_player_same_name_returns_400(self, client):
        c, conn = client
        db.get_or_create_player(conn, "Player1")
        conn.commit()
        
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Player1", "new_name": "Player1"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_rename_player_missing_fields_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Player1"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── /api/snapshot/<id>/add-player ─────────────────────────────────────────────

class TestApiAddPlayer:
    def test_add_player_success(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn, players=1)
        conn.commit()
        
        resp = c.post(
            f"/api/snapshot/{snap_id}/add-player",
            data=json.dumps({
                "nombre": "NewPlayer",
                "experiencia": "Nuevo",
                "juegos_este_ano": 0,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "player_id" in data
        
        # Verify the player was added
        players = db.get_snapshot_players(conn, snap_id)
        nombres = [p["nombre"] for p in players]
        assert "NewPlayer" in nombres

    def test_add_player_nonexistent_snapshot_returns_404(self, client):
        c, conn = client
        resp = c.post(
            "/api/snapshot/9999/add-player",
            data=json.dumps({"nombre": "NewPlayer"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_add_player_missing_nombre_returns_400(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn, players=1)
        conn.commit()
        
        resp = c.post(
            f"/api/snapshot/{snap_id}/add-player",
            data=json.dumps({"experiencia": "Nuevo"}),
            content_type="application/json",
        )
        assert resp.status_code == 400