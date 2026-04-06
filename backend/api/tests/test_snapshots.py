"""
test_snapshots.py — Tests for /api/snapshot endpoints.

Tests snapshot CRUD operations and deletion cascade.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from backend.crud.chain import create_game_edge
from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
    get_snapshot_players,
)
from backend.db.models import Snapshot, SnapshotHistory, SnapshotPlayer, TimelineEdge

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def make_snapshot_with_players(
    db_session: Any, n: int = 5, source: str = "notion_sync"
) -> int:
    """Creates a snapshot with n players and returns snapshot_id."""
    snap_id = await create_snapshot(db_session, source)
    for i in range(n):
        pid = await get_or_create_player(db_session, f"P{snap_id}_{i}")
        await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", 0, 1, 2, 0)
    await db_session.commit()
    return snap_id


# ── GET /api/snapshot/<id> ────────────────────────────────────────────────────


class TestApiSnapshotDetail:
    async def test_snapshot_not_found(self, client: Any) -> None:
        resp = await client.get("/api/snapshot/99999")
        assert resp.status_code == 404

    async def test_snapshot_found_returns_player_list(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, n=3)
        resp = await client.get(f"/api/snapshot/{snap_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == snap_id
        assert "players" in data
        assert len(data["players"]) == 3
        # Check player data structure
        if data["players"]:
            p = data["players"][0]
            for key in ("nombre", "experiencia", "juegos_este_ano"):
                assert key in p

    async def test_snapshot_includes_source(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, n=1, source="manual")
        resp = await client.get(f"/api/snapshot/{snap_id}")
        data = resp.json()
        assert data["source"] == "manual"


# ── GET /api/snapshot ─────────────────────────────────────────────────────────


class TestApiSnapshotList:
    async def test_empty_list(self, client: Any) -> None:
        resp = await client.get("/api/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshots"] == []

    async def test_list_returns_snapshots(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, n=5)
        resp = await client.get("/api/snapshot")
        data = resp.json()
        assert len(data["snapshots"]) >= 1
        ids = [s["id"] for s in data["snapshots"]]
        assert snap_id in ids

    async def test_list_includes_player_count(self, client: Any, db_session: Any) -> None:
        await make_snapshot_with_players(db_session, n=7)
        resp = await client.get("/api/snapshot")
        data = resp.json()
        for snap in data["snapshots"]:
            assert "player_count" in snap


# ── DELETE /api/snapshot/<id> ─────────────────────────────────────────────────


class TestApiSnapshotDelete:
    async def test_delete_nonexistent_returns_404(self, client: Any) -> None:
        resp = await client.delete("/api/snapshot/99999")
        assert resp.status_code == 404

    async def test_delete_snapshot_removes_it(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, n=5)
        resp = await client.delete(f"/api/snapshot/{snap_id}")
        assert resp.status_code == 200
        # Verify deleted
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_id))
        assert result.scalar_one_or_none() is None

    async def test_delete_cascade_removes_players(self, client: Any, db_session: Any) -> None:
        """Deleting a snapshot should remove its SnapshotPlayer entries."""
        snap_id = await make_snapshot_with_players(db_session, n=5)
        # Get player IDs before delete
        result = await db_session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snap_id)
        )
        before_count = len(result.scalars().all())
        assert before_count == 5
        # Delete snapshot
        await client.delete(f"/api/snapshot/{snap_id}")
        await db_session.commit()
        # Verify cascade delete worked
        result = await db_session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snap_id)
        )
        after_count = len(result.scalars().all())
        assert after_count == 0

    async def test_delete_with_game_event_cascade(self, client: Any, db_session: Any) -> None:
        """Deleting a snapshot should cascade to related game events and their data."""
        snap1 = await make_snapshot_with_players(db_session, n=14)
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()
        # Create a game event linking snap1 -> snap2
        edge_id = await create_game_edge(db_session, snap1, snap2, 1)
        await db_session.commit()
        # Delete the source snapshot
        resp = await client.delete(f"/api/snapshot/{snap1}")
        assert resp.status_code == 200
        await db_session.commit()
        # Expire all to force fresh query
        db_session.expire_all()
        # Verify game event is deleted
        result = await db_session.execute(select(TimelineEdge).where(TimelineEdge.id == edge_id))
        assert result.scalar_one_or_none() is None

    async def test_delete_sibling_triggers_squash(self, client: Any, db_session: Any) -> None:
        """
        Regression test: When a snapshot has two children (Game -> B, Manual -> C)
        and we delete B, snapshot C should be squashed into A.

        This verifies the fix where:
        1. session.flush() is called before squashing
        2. squash_linear_branch receives the parent snapshot ID
        3. Any non-game edge is squashed (not just "branch")
        4. Source and created_at are inherited from the child
        """
        from backend.crud.chain import create_branch_edge
        from backend.crud.snapshots import get_snapshot_players

        # Setup: A -> Game -> B
        #        A -> Manual -> C
        snap_a = await make_snapshot_with_players(db_session, n=5, source="notion_sync")
        snap_b = await create_snapshot(db_session, "organizar")
        snap_c = await create_snapshot(db_session, "manual")

        # Add different players to C to verify squashing
        pid_c1 = await get_or_create_player(db_session, "PlayerC1")
        pid_c2 = await get_or_create_player(db_session, "PlayerC2")
        await add_player_to_snapshot(db_session, snap_c, pid_c1, "Antiguo", 5, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap_c, pid_c2, "Nuevo", 2, 1, 1, 0)

        # Create edges: A -> game -> B and A -> branch -> C
        _game_edge_id = await create_game_edge(db_session, snap_a, snap_b, 1)
        branch_edge_id = await create_branch_edge(db_session, snap_a, snap_c)
        await db_session.commit()

        # Get C's original source and timestamp for verification
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_c))
        snap_c_obj = result.scalar_one()
        c_source = snap_c_obj.source
        c_timestamp = snap_c_obj.created_at

        # Verify initial state: A has 2 outgoing edges
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snap_a)
        )
        assert len(result.scalars().all()) == 2

        # Action: Delete snapshot B
        resp = await client.delete(f"/api/snapshot/{snap_b}")
        assert resp.status_code == 200
        await db_session.commit()
        db_session.expire_all()

        # Assert 1: Snapshot B is gone
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is None

        # Assert 2: Snapshot C is also gone (squashed into A)
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_c))
        assert result.scalar_one_or_none() is None

        # Assert 3: Snapshot A still exists
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        snap_a_obj = result.scalar_one()
        assert snap_a_obj is not None

        # Assert 4: A's roster is now C's roster
        players_a = await get_snapshot_players(db_session, snap_a)
        assert len(players_a) == 2
        player_names = {p["nombre"] for p in players_a}
        assert player_names == {"PlayerC1", "PlayerC2"}

        # Assert 5: A inherited C's source and timestamp
        assert snap_a_obj.source == c_source
        assert snap_a_obj.created_at == c_timestamp

        # Assert 6: A has no outgoing edges now (both B and C edges removed)
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snap_a)
        )
        assert len(result.scalars().all()) == 0

        # Assert 7: The branch edge from A to C is gone
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.id == branch_edge_id)
        )
        assert result.scalar_one_or_none() is None


# ── POST /api/snapshot ─────────────────────────────────────────────────────────


class TestApiSnapshotCreate:
    async def test_create_without_parent(self, client: Any) -> None:
        """Creating a snapshot without parent_id creates a root snapshot."""
        resp = await client.post(
            "/api/snapshot",
            json={"source": "manual", "players": []},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        # FastAPI returns snapshot_id
        snap_id = data.get("snapshot_id") or data.get("id")
        assert snap_id is not None

    async def test_create_with_parent(self, client: Any, db_session: Any) -> None:
        """Creating a snapshot with parent_id links it to parent."""
        parent_id = await make_snapshot_with_players(db_session, n=5)
        resp = await client.post(
            "/api/snapshot",
            json={
                "source": "manual",
                "parent_id": parent_id,
                "players": [],
            },
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        # Verify the new snapshot is linked to parent via an event
        new_id = data["snapshot_id"]
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.output_snapshot_id == new_id)
        )
        edge = result.scalar_one_or_none()
        assert edge is not None
        assert edge.source_snapshot_id == parent_id

    async def test_create_preserves_roster_in_place(self, client: Any, db_session: Any) -> None:
        """Creating a snapshot with same roster as parent should detect no changes and skip history."""
        parent_id = await make_snapshot_with_players(db_session, n=5)
        # Get current player list
        players_before = await get_snapshot_players(db_session, parent_id)
        # Create child with same roster (this should trigger no_changes via /api/snapshot/save)
        resp = await client.post(
            "/api/snapshot/save",
            json={
                "parent_id": parent_id,
                "event_type": "manual",
                "players": players_before,
            },
        )
        # Should detect no changes and return early
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot_id"] == parent_id
        assert data["status"] == "no_changes"

        # No SnapshotHistory entry should be created when there are no changes
        result = await db_session.execute(
            select(SnapshotHistory).where(SnapshotHistory.snapshot_id == parent_id)
        )
        history_records = result.scalars().all()
        assert len(history_records) == 0

    async def test_create_snapshot_adds_players(self, client: Any, db_session: Any) -> None:
        """Creating a snapshot should add provided players."""
        players = [
            {
                "nombre": f"Player{i}",
                "experiencia": "Antiguo",
                "juegos_este_ano": i,
                "prioridad": 1,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            }
            for i in range(3)
        ]
        resp = await client.post(
            "/api/snapshot",
            json={"source": "manual", "players": players},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        snap_id = data["snapshot_id"]
        # Verify players were added
        from backend.crud.snapshots import get_snapshot_players

        db_players = await get_snapshot_players(db_session, snap_id)
        assert len(db_players) == 3


# ── POST /api/snapshot/<id>/save ──────────────────────────────────────────────


class TestApiSnapshotSave:
    async def test_save_snapshot_manual(self, client: Any, db_session: Any) -> None:
        """Saving a snapshot should update its players and metadata."""
        snap_id = await make_snapshot_with_players(db_session, n=3)
        new_players = [
            {
                "nombre": f"NewPlayer{i}",
                "experiencia": "Nuevo",
                "juegos_este_ano": 0,
                "prioridad": 1,
                "partidas_deseadas": 1,
                "partidas_gm": 0,
            }
            for i in range(2)
        ]
        resp = await client.post(
            f"/api/snapshot/{snap_id}/save",
            json={
                "source": "manual",
                "players": new_players,
            },
        )
        assert resp.status_code == 200
        # Verify players were replaced
        from backend.crud.snapshots import get_snapshot_players

        db_players = await get_snapshot_players(db_session, snap_id)
        assert len(db_players) == 2
        names = {p["nombre"] for p in db_players}
        assert names == {"NewPlayer0", "NewPlayer1"}

    async def test_save_notion_sync(self, client: Any, db_session: Any) -> None:
        """Saving with notion_sync source should work."""
        parent_id = await make_snapshot_with_players(db_session, n=5)
        resp = await client.post(
            f"/api/snapshot/{parent_id}/save",
            json={
                "source": "notion_sync",
                "players": [],
            },
        )
        assert resp.status_code in (200, 201)

    async def test_save_creates_branch_edge(self, client: Any, db_session: Any) -> None:
        """POST /api/snapshot/save must create a TimelineEdge with edge_type='branch'."""
        # Setup: Create parent snapshot with players and a child (so parent is not a leaf)
        parent_id = await make_snapshot_with_players(db_session, n=3)
        # Create a game event to make parent non-leaf (has a child)
        child_id = await create_snapshot(db_session, "organizar")
        await create_game_edge(db_session, parent_id, child_id, 1)
        await db_session.commit()

        # Action: Save with modified player list (parent is now internal node, so new snapshot created)
        new_players = [
            {
                "nombre": f"ModifiedPlayer{i}",
                "experiencia": "Antiguo",
                "juegos_este_ano": i,
                "prioridad": 1,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            }
            for i in range(2)
        ]
        resp = await client.post(
            "/api/snapshot/save",
            json={
                "parent_id": parent_id,
                "event_type": "manual",
                "players": new_players,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        new_snap_id = data["snapshot_id"]

        # Assert: Query TimelineEdge and verify edge_type is 'branch'
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.output_snapshot_id == new_snap_id)
        )
        edges = result.scalars().all()
        assert len(edges) == 1, f"Expected exactly 1 edge, got {len(edges)}"
        edge = edges[0]
        assert edge.edge_type == "branch", f"Expected edge_type='branch', got '{edge.edge_type}'"

    async def test_snapshot_save_ignores_algorithm_weights(
        self, client: Any, db_session: Any
    ) -> None:
        """
        Regression test: Algorithm weight fields (c_england, c_france, etc.)
        should be ignored during snapshot save to prevent phantom modifications.
        
        When saving a sync with the same roster but extra algorithm fields,
        the backend should detect no actual changes and return "no_changes".
        """
        # Setup: Create a root snapshot with only Juan using the dedicated helper
        from backend.crud.snapshots import create_root_manual_snapshot
        
        parent_id = await create_root_manual_snapshot(
            db_session,
            players=[
                {
                    "nombre": "Juan",
                    "experiencia": "Nuevo",
                    "juegos_este_ano": 0,
                    "prioridad": 0,
                    "partidas_deseadas": 1,
                    "partidas_gm": 0,
                }
            ],
        )
        await db_session.commit()
        
        # Verify setup: snapshot should have exactly 1 player
        players_before = await get_snapshot_players(db_session, parent_id)
        assert len(players_before) == 1
        assert players_before[0]["nombre"] == "Juan"
        
        # The Action: Save with same player data BUT include algorithm weights
        # These should be ignored and not trigger a phantom modification
        resp = await client.post(
            "/api/snapshot/save",
            json={
                "parent_id": parent_id,
                "event_type": "sync",
                "players": [
                    {
                        "nombre": "Juan",
                        "experiencia": "Nuevo",
                        "juegos_este_ano": 0,
                        "prioridad": 0,
                        "partidas_deseadas": 1,
                        "partidas_gm": 0,
                        # These algorithm fields should be ignored
                        "c_england": 5,
                        "c_france": 3,
                    }
                ],
            },
        )
        
        # The Assertion: Backend should ignore extra fields and detect no changes
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "no_changes"
        assert data["snapshot_id"] == parent_id
