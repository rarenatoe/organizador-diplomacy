"""
test_viewer_snapshot.py — Tests for /api/snapshot endpoints.

Tests snapshot CRUD operations and editing.
"""
from __future__ import annotations

import json

import pytest

from backend.db import db
from .conftest import _add_snapshot


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


# ── DELETE /api/snapshot/<id> ───────────────────────────────────────────────────

class TestApiDeleteSnapshot:
    def test_delete_existing_snapshot_returns_200(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn)
        conn.commit()
        resp = c.delete(f"/api/snapshot/{snap_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert snap_id in data["deleted"]

    def test_delete_nonexistent_snapshot_returns_404(self, client):
        c, conn = client
        resp = c.delete("/api/snapshot/9999")
        assert resp.status_code == 404

    def test_delete_removes_snapshot_from_chain(self, client):
        """After deletion the snapshot no longer appears in /api/chain."""
        c, conn = client
        snap_id = _add_snapshot(conn)
        conn.commit()
        c.delete(f"/api/snapshot/{snap_id}")
        chain = c.get("/api/chain").get_json()
        ids = [n["id"] for n in chain["roots"]]
        assert snap_id not in ids

    def test_delete_cascades_sync_event_via_api(self, client):
        """Deleting the output snapshot of a sync event returns both IDs deleted."""
        c, conn = client
        snap1 = _add_snapshot(conn)
        snap2 = _add_snapshot(conn)
        db.create_sync_event(conn, snap1, snap2)
        conn.commit()
        resp = c.delete(f"/api/snapshot/{snap2}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert snap2 in data["deleted"]
        # snap1 must NOT be in deleted list
        assert snap1 not in data["deleted"]


class TestApiCreateSnapshot:
    def test_create_new_snapshot_success(self, client):
        """POST /api/snapshot/new creates a new root snapshot and returns the ID."""
        c, conn = client
        players_list = [
            {"nombre": "Alice", "experiencia": "Nuevo", "juegos_este_ano": 0,
             "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0},
            {"nombre": "Bob", "experiencia": "Antiguo", "juegos_este_ano": 3,
             "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 1},
        ]
        resp = c.post(
            "/api/snapshot/new",
            data=json.dumps({"players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "snapshot_id" in data
        new_id = data["snapshot_id"]
        
        # Verify the snapshot was created with correct players
        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        assert detail["source"] == "manual"
        assert len(detail["players"]) == 2
        player_names = {p["nombre"] for p in detail["players"]}
        assert player_names == {"Alice", "Bob"}

    def test_create_new_snapshot_empty_players(self, client):
        """POST /api/snapshot/new with empty players list creates snapshot with no players."""
        c, conn = client
        resp = c.post(
            "/api/snapshot/new",
            data=json.dumps({"players": []}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "snapshot_id" in data
        new_id = data["snapshot_id"]
        
        # Verify the snapshot was created with no players
        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        assert detail["source"] == "manual"
        assert len(detail["players"]) == 0

    def test_create_new_snapshot_invalid_players_type_returns_400(self, client):
        """POST /api/snapshot/new with invalid players type returns 400."""
        c, conn = client
        resp = c.post(
            "/api/snapshot/new",
            data=json.dumps({"players": "not_a_list"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_create_new_snapshot_applies_defaults(self, client):
        """POST /api/snapshot/new applies default values for missing fields."""
        c, conn = client
        # Only provide nombre, omit other fields
        players_list = [
            {"nombre": "Charlie"},
        ]
        resp = c.post(
            "/api/snapshot/new",
            data=json.dumps({"players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_id = resp.get_json()["snapshot_id"]
        
        # Verify defaults were applied
        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        player = detail["players"][0]
        assert player["nombre"] == "Charlie"
        assert player["experiencia"] == "Nuevo"
        assert player["juegos_este_ano"] == 0
        assert player["prioridad"] == 0
        assert player["partidas_deseadas"] == 1
        assert player["partidas_gm"] == 0


class TestApiSnapshotSave:
    def test_save_creates_manual_snapshot(self, client):
        """POST /api/snapshot/save with event_type='manual' creates a manual snapshot."""
        c, conn = client
        players_list = [
            {"nombre": "Alice", "experiencia": "Nuevo", "juegos_este_ano": 0},
            {"nombre": "Bob", "experiencia": "Antiguo", "juegos_este_ano": 3},
        ]
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"event_type": "manual", "players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "snapshot_id" in data
        new_id = data["snapshot_id"]

        # Verify the snapshot was created with correct source
        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        assert detail["source"] == "manual"
        assert len(detail["players"]) == 2

    def test_save_creates_sync_snapshot(self, client):
        """POST /api/snapshot/save with event_type='sync' creates a notion_sync snapshot."""
        c, conn = client
        players_list = [{"nombre": "Charlie", "experiencia": "Nuevo", "juegos_este_ano": 0}]
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"event_type": "sync", "players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_id = resp.get_json()["snapshot_id"]

        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        assert detail["source"] == "notion_sync"

    def test_save_with_parent_creates_event(self, client):
        """POST /api/snapshot/save with parent_id creates an event linking parent to new snapshot."""
        c, conn = client
        parent_id = _add_snapshot(conn, players=2)
        conn.commit()

        players_list = [{"nombre": "Dave", "experiencia": "Nuevo", "juegos_este_ano": 0}]
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"parent_id": parent_id, "event_type": "manual", "players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_id = resp.get_json()["snapshot_id"]

        # Verify event was created
        event = conn.execute(
            "SELECT type, source_snapshot_id, output_snapshot_id FROM events WHERE output_snapshot_id = ?",
            (new_id,)
        ).fetchone()
        assert event is not None
        assert event["type"] == "edit"  # 'manual' event_type maps to 'edit' in DB
        assert event["source_snapshot_id"] == parent_id
        assert event["output_snapshot_id"] == new_id

    def test_save_without_parent_no_event(self, client):
        """POST /api/snapshot/save without parent_id creates no event."""
        c, conn = client
        players_list = [{"nombre": "Eve", "experiencia": "Nuevo", "juegos_este_ano": 0}]
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"event_type": "manual", "players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_id = resp.get_json()["snapshot_id"]

        # Verify no event was created
        event = conn.execute(
            "SELECT 1 FROM events WHERE output_snapshot_id = ?",
            (new_id,)
        ).fetchone()
        assert event is None

    def test_save_applies_defaults(self, client):
        """POST /api/snapshot/save applies default values for missing fields."""
        c, conn = client
        players_list = [{"nombre": "Frank"}]
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"event_type": "manual", "players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_id = resp.get_json()["snapshot_id"]

        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        player = detail["players"][0]
        assert player["nombre"] == "Frank"
        assert player["experiencia"] == "Nuevo"
        assert player["juegos_este_ano"] == 0
        assert player["prioridad"] == 0
        assert player["partidas_deseadas"] == 1
        assert player["partidas_gm"] == 0

    def test_save_invalid_players_type_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"event_type": "manual", "players": "not_a_list"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_invalid_event_type_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"event_type": "invalid", "players": []}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_nonexistent_parent_returns_404(self, client):
        c, conn = client
        resp = c.post(
            "/api/snapshot/save",
            data=json.dumps({"parent_id": 9999, "event_type": "manual", "players": []}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestApiNotionFetch:
    def test_fetch_returns_players_list(self, client, monkeypatch):
        """GET /api/notion/fetch returns players from Notion."""
        c, conn = client

        # Mock the Notion Client class at the import location
        class MockClient:
            def __init__(self, auth=None):
                self.auth = auth

            class databases:
                @staticmethod
                def retrieve(database_id=None):
                    return {"data_sources": [{"id": "ds-1"}]}

            class data_sources:
                @staticmethod
                def query(**kwargs):
                    return {
                        "results": [
                            {
                                "id": "page-1",
                                "properties": {
                                    "Nombre": {"title": [{"plain_text": "Alice"}]},
                                    "Participaciones": {"relation": []},
                                },
                            },
                            {
                                "id": "page-2",
                                "properties": {
                                    "Nombre": {"title": [{"plain_text": "Bob"}]},
                                    "Participaciones": {"relation": [{"id": "rel-1"}]},
                                },
                            },
                        ],
                        "has_more": False,
                    }

        # Patch at the viewer module level where Client is imported
        monkeypatch.setattr("backend.viewer.viewer.Client", MockClient)
        monkeypatch.setenv("NOTION_TOKEN", "secret_test")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-test")
        monkeypatch.setenv("NOTION_PARTICIPACIONES_DB_ID", "part-test")

        resp = c.get("/api/notion/fetch")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "players" in data
        assert len(data["players"]) == 2

        # Verify player data
        players = {p["nombre"]: p for p in data["players"]}
        assert players["Alice"]["experiencia"] == "Nuevo"
        assert players["Alice"]["juegos_este_ano"] == 0
        assert players["Bob"]["experiencia"] == "Antiguo"
        assert players["Bob"]["juegos_este_ano"] == 0  # Mock returns 0 for conteo

    def test_fetch_missing_token_returns_500(self, client, monkeypatch):
        """GET /api/notion/fetch returns 500 if NOTION_TOKEN is not configured."""
        c, conn = client
        # Mock load_dotenv to not load .env file
        monkeypatch.setattr("backend.viewer.viewer.load_dotenv", lambda: None)
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-test")
        monkeypatch.setenv("NOTION_PARTICIPACIONES_DB_ID", "part-test")

        resp = c.get("/api/notion/fetch")
        assert resp.status_code == 500
        assert "NOTION_TOKEN" in resp.get_json()["error"]

    def test_fetch_missing_database_id_returns_500(self, client, monkeypatch):
        """GET /api/notion/fetch returns 500 if NOTION_DATABASE_ID is not configured."""
        c, conn = client
        # Mock load_dotenv to not load .env file
        monkeypatch.setattr("backend.viewer.viewer.load_dotenv", lambda: None)
        monkeypatch.setenv("NOTION_TOKEN", "secret_test")
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        monkeypatch.setenv("NOTION_PARTICIPACIONES_DB_ID", "part-test")

        resp = c.get("/api/notion/fetch")
        assert resp.status_code == 500
        assert "NOTION_DATABASE_ID" in resp.get_json()["error"]
