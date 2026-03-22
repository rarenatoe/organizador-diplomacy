"""
test_viewer_chain.py — Tests for /api/chain endpoint.

Tests the chain data structure and snapshot relationships.
"""
from __future__ import annotations

import json

import pytest

from backend.db import db, db_game
from .conftest import _add_snapshot


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

        db_game.create_game_event(conn, snap1, snap2, 1, "copypaste1")
        db_game.create_game_event(conn, snap1, snap3, 1, "copypaste2")
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