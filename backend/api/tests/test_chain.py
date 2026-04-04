"""
test_chain.py — Tests for /api/chain endpoint.

Tests the chain data structure and snapshot relationships.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.db.crud import create_game_edge, create_snapshot

pytestmark = pytest.mark.asyncio


# ── /api/chain ────────────────────────────────────────────────────────────────


class TestApiChain:
    async def test_empty_db_returns_empty_roots(self, client: Any) -> None:
        resp = await client.get("/api/chain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["roots"] == []

    async def test_single_snapshot_is_root(self, client: Any, db_session: Any) -> None:
        from backend.conftest import add_snapshot

        await add_snapshot(db_session, players=3)
        resp = await client.get("/api/chain")
        data = resp.json()
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["type"] == "snapshot"
        assert root["player_count"] == 3
        assert root["branches"] == []

    async def test_sync_branch_not_a_root(self, client: Any, db_session: Any) -> None:
        """Snapshot produced by a sync_event must be a branch, not a root."""
        from backend.conftest import add_snapshot
        from backend.db.crud import create_branch_edge

        snap1 = await add_snapshot(db_session)
        snap2 = await add_snapshot(db_session)
        await create_branch_edge(db_session, snap1, snap2)
        await db_session.commit()
        resp = await client.get("/api/chain")
        data = resp.json()
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["id"] == snap1
        assert len(root["branches"]) == 1
        branch = root["branches"][0]
        assert branch["edge"]["type"] == "branch"
        assert branch["output"]["id"] == snap2

    async def test_latest_flag_on_highest_id(self, client: Any, db_session: Any) -> None:
        """is_latest is True only on the snapshot with the highest id."""
        from backend.conftest import add_snapshot
        from backend.db.crud import create_branch_edge

        snap1 = await add_snapshot(db_session)
        snap2 = await add_snapshot(db_session)
        await create_branch_edge(db_session, snap1, snap2)
        await db_session.commit()
        resp = await client.get("/api/chain")
        data = resp.json()
        root = data["roots"][0]
        assert root["is_latest"] is False
        assert root["branches"][0]["output"]["is_latest"] is True

    async def test_two_branches_from_same_snapshot(self, client: Any, db_session: Any) -> None:
        """
        Regression: two game_events reading from snap1 must produce two sibling
        branches of snap1, not a chain snap1→game_A→snap2→game_B→snap3.
        """
        from backend.conftest import add_snapshot

        snap1 = await add_snapshot(db_session, players=14)
        snap2 = await create_snapshot(db_session, "organizar")
        snap3 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        await create_game_edge(db_session, snap1, snap2, 1)
        await create_game_edge(db_session, snap1, snap3, 1)
        await db_session.commit()

        resp = await client.get("/api/chain")
        data = resp.json()
        # snap1 is the only root; snap2 and snap3 are children
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["id"] == snap1
        assert len(root["branches"]) == 2
        output_ids = {b["output"]["id"] for b in root["branches"]}
        assert output_ids == {snap2, snap3}
