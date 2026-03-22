"""
test_viewer_snapshot.py — Tests for /api/snapshot endpoints.

Tests snapshot CRUD operations and editing.
"""
from __future__ import annotations

import json

import pytest

from . import db
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


class TestApiEditSnapshot:
    def test_edit_creates_new_manual_snapshot(self, client):
        """POST /api/snapshot/<id>/edit returns 200 with new snapshot_id."""
        c, conn = client
        snap_id = _add_snapshot(conn, players=3)
        conn.commit()
        names = [p["nombre"] for p in db.get_snapshot_players(conn, snap_id)]
        players_list = [
            {"nombre": n, "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0}
            for n in names
        ]
        resp = c.post(
            f"/api/snapshot/{snap_id}/edit",
            data=json.dumps({"players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "snapshot_id" in data
        assert data["snapshot_id"] != snap_id

    def test_edit_nonexistent_snapshot_returns_404(self, client):
        c, conn = client
        resp = c.post(
            "/api/snapshot/9999/edit",
            data=json.dumps({"players": []}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_edit_invalid_players_type_returns_400(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn)
        conn.commit()
        resp = c.post(
            f"/api/snapshot/{snap_id}/edit",
            data=json.dumps({"players": "not_a_list"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_edit_new_snapshot_has_manual_source(self, client):
        """The snapshot created by the edit endpoint has source='manual'."""
        c, conn = client
        snap_id = _add_snapshot(conn, players=1)
        conn.commit()
        names = [p["nombre"] for p in db.get_snapshot_players(conn, snap_id)]
        resp = c.post(
            f"/api/snapshot/{snap_id}/edit",
            data=json.dumps({"players": [
                {"nombre": names[0], "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0}
            ]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_id = resp.get_json()["snapshot_id"]
        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        assert detail["source"] == "manual"