"""
test_snapshots.py — Tests for /api/snapshot endpoints.

Tests snapshot CRUD operations and deletion cascade.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

import pytest
from sqlalchemy import select

from backend.crud.chain import create_branch_edge, create_game_edge
from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
    get_snapshot_players,
)
from backend.db.models import (
    Snapshot,
    SnapshotHistory,
    SnapshotPlayer,
    SnapshotSource,
    TimelineEdge,
)

if TYPE_CHECKING:
    from typing import Any

    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


class ManualSnapshotPlayer(TypedDict):
    nombre: str
    is_new: bool
    juegos_este_ano: int
    has_priority: bool
    partidas_deseadas: int
    partidas_gm: int
    notion_id: NotRequired[str | None]


@pytest.mark.asyncio
async def test_api_snapshot_save_branch_logs_history(client: AsyncClient, db_session: AsyncSession):
    """
    Ensures that when a snapshot save creates a NEW branch (because the parent
    is an internal node with existing children), the diff between the parent
    and the new branch is successfully logged to SnapshotHistory.
    """

    # 1. Setup: Create a parent snapshot with one player
    parent_id = await create_snapshot(db_session, source=SnapshotSource.MANUAL)
    p1_id = await get_or_create_player(db_session, "Alice", None)
    await add_player_to_snapshot(
        db_session,
        parent_id,
        p1_id,
        has_priority=False,
        is_new=True,
        games_this_year=0,
        desired_games=1,
        gm_games=0,
    )

    # 2. Setup: Force the parent to be an 'internal node' by giving it a child
    child_id = await create_snapshot(db_session, source=SnapshotSource.MANUAL)
    edge = TimelineEdge(
        source_snapshot_id=parent_id,
        output_snapshot_id=child_id,
        id=1,
        edge_type="game",
    )
    db_session.add(edge)
    await db_session.commit()

    # 3. Action: Call /api/snapshot/save targeting the parent, modifying the roster
    payload = {
        "parent_id": parent_id,
        "event_type": "manual",
        "players": [
            {
                "nombre": "Alice",
                "juegos_este_ano": 1,  # Modified value
                "is_new": True,
                "has_priority": False,
                "partidas_deseadas": 1,
                "partidas_gm": 0,
            },
            {
                "nombre": "Bob",  # Added player
                "juegos_este_ano": 0,
                "is_new": True,
                "has_priority": False,
                "partidas_deseadas": 1,
                "partidas_gm": 0,
            },
        ],
        "renames": [],
    }

    response = await client.post("/api/snapshot/save", json=payload)
    assert response.status_code == 200
    data = response.json()
    new_snap_id = data["snapshot_id"]

    # Verify a branch was actually created
    assert new_snap_id != parent_id, "Expected a new snapshot branch to be created"
    assert new_snap_id != child_id, "Expected a totally new snapshot ID"

    # 4. Assert: Check that SnapshotHistory was created for the new branch
    result = await db_session.execute(
        select(SnapshotHistory).where(SnapshotHistory.snapshot_id == new_snap_id)
    )
    history_logs = result.scalars().all()

    assert len(history_logs) > 0, "Expected history to be logged upon branch creation"

    # 5. Assert: Verify the diff correctly captured the changes
    changes = history_logs[0].changes

    # 'added' is a list of strings
    assert "Bob" in changes.get("added", []), "Expected 'Bob' to be registered as added"

    # 'modified' is a list of dictionaries, so we use a generator expression to find Alice
    assert any(mod.get("nombre") == "Alice" for mod in changes.get("modified", [])), (
        "Expected 'Alice' to be registered as modified"
    )


async def make_snapshot_with_players(
    db_session: Any, n: int = 5, source: SnapshotSource = SnapshotSource.NOTION_SYNC
) -> int:
    """Creates a snapshot with n players and returns snapshot_id."""
    snap_id = await create_snapshot(db_session, source)
    for i in range(n):
        pid = await get_or_create_player(db_session, f"P{snap_id}_{i}")
        await add_player_to_snapshot(
            db_session,
            snap_id,
            pid,
            games_this_year=0,
            desired_games=2,
            gm_games=0,
            has_priority=True,
            is_new=False,
        )
    await db_session.commit()
    return snap_id


async def make_root_manual_snapshot(
    db_session: Any,
    players: list[ManualSnapshotPlayer],
) -> int:
    """Create a root manual snapshot for test setup only."""
    snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)

    for player in players:
        name = player["nombre"]
        if not name:
            continue

        player_id = await get_or_create_player(
            db_session,
            name,
            player.get("notion_id"),
        )
        await add_player_to_snapshot(
            db_session,
            snap_id,
            player_id,
            player["juegos_este_ano"],
            player["partidas_deseadas"],
            player["partidas_gm"],
            has_priority=player["has_priority"],
            is_new=player["is_new"],
        )

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
            for key in ("nombre", "is_new", "juegos_este_ano"):
                assert key in p

    async def test_snapshot_includes_source(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, n=1, source=SnapshotSource.MANUAL)
        resp = await client.get(f"/api/snapshot/{snap_id}")
        data = resp.json()
        assert data["source"] == "manual"

    async def test_snapshot_ignores_malformed_history_changes(
        self, client: Any, db_session: Any
    ) -> None:
        """Malformed legacy history rows must not crash snapshot detail endpoint."""
        snap_id = await make_snapshot_with_players(db_session, n=1, source=SnapshotSource.MANUAL)
        bad_history = SnapshotHistory(
            snapshot_id=snap_id,
            action_type=SnapshotSource.MANUAL_EDIT,
            changes={"invalid": "payload"},
            previous_state={"players": []},
        )
        db_session.add(bad_history)
        await db_session.commit()

        resp = await client.get(f"/api/snapshot/{snap_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == snap_id
        assert data["history"] == []


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
        snap2 = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)
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

    async def test_delete_snapshot_deep_recursive_cascade(
        self, client: Any, db_session: Any
    ) -> None:
        """Deleting a root snapshot should recursively delete children and grandchildren, leaving no stray nodes."""
        snap1 = await make_snapshot_with_players(db_session, n=5)
        snap2 = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)
        snap3 = await create_snapshot(db_session, SnapshotSource.MANUAL)

        # Create Chain: snap1 -> (game) -> snap2 -> (branch) -> snap3
        edge1_id = await create_game_edge(db_session, snap1, snap2, 1)
        edge2_id = await create_branch_edge(db_session, snap2, snap3)
        await db_session.commit()

        # Action: Delete the root snapshot
        resp = await client.delete(f"/api/snapshot/{snap1}")
        assert resp.status_code == 200
        await db_session.commit()
        db_session.expire_all()

        # Verify all snapshots in the chain are deleted (no stray orphans)
        for snap_id in [snap1, snap2, snap3]:
            result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_id))
            assert result.scalar_one_or_none() is None

        # Verify all connecting edges are deleted
        for edge_id in [edge1_id, edge2_id]:
            result = await db_session.execute(
                select(TimelineEdge).where(TimelineEdge.id == edge_id)
            )
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
        from backend.crud.snapshots import get_snapshot_players

        # Setup: A -> Game -> B
        #        A -> Manual -> C
        snap_a = await make_snapshot_with_players(
            db_session, n=5, source=SnapshotSource.NOTION_SYNC
        )
        snap_b = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)
        snap_c = await create_snapshot(db_session, SnapshotSource.MANUAL)

        # Add different players to C to verify squashing
        pid_c1 = await get_or_create_player(db_session, "PlayerC1")
        pid_c2 = await get_or_create_player(db_session, "PlayerC2")
        await add_player_to_snapshot(
            db_session, snap_c, pid_c1, 5, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, snap_c, pid_c2, 2, 1, 0, has_priority=True, is_new=True
        )

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
        player_names = {p.nombre for p in players_a}
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


# ── POST /api/snapshot/<id>/save ──────────────────────────────────────────────


class TestApiSnapshotSave:
    async def test_save_rejects_invalid_event_type(self, client: Any, db_session: Any) -> None:
        parent_id = await make_snapshot_with_players(db_session, n=2)

        resp = await client.post(
            "/api/snapshot/save",
            json={
                "parent_id": parent_id,
                "event_type": "edit",
                "players": [],
            },
        )

        assert resp.status_code == 422

    async def test_save_snapshot_manual(self, client: Any, db_session: Any) -> None:
        """Saving a snapshot should update its players, metadata, and notion_ids."""
        snap_id = await make_snapshot_with_players(db_session, n=3)
        new_players = [
            {
                "nombre": f"NewPlayer{i}",
                "notion_id": f"new_notion_{i}",
                "is_new": True,
                "juegos_este_ano": 0,
                "has_priority": True,
                "partidas_deseadas": 1,
                "partidas_gm": 0,
            }
            for i in range(2)
        ]
        resp = await client.post(
            "/api/snapshot/save",
            json={"parent_id": snap_id, "event_type": "manual", "players": new_players},
        )
        assert resp.status_code == 200

        # Verify players were replaced
        from backend.crud.snapshots import get_snapshot_players

        db_players = await get_snapshot_players(db_session, snap_id)
        assert len(db_players) == 2
        names = {p.nombre for p in db_players}
        assert names == {"NewPlayer0", "NewPlayer1"}

        # Verify notion_id was saved
        from sqlalchemy import select

        from backend.db.models import Player

        for i in range(2):
            res = await db_session.execute(select(Player).where(Player.name == f"NewPlayer{i}"))
            player_record = res.scalar_one()
            assert player_record.notion_id == f"new_notion_{i}"

    async def test_save_notion_sync(self, client: Any, db_session: Any) -> None:
        """Saving with notion_sync source should work."""
        parent_id = await make_snapshot_with_players(db_session, n=5)
        resp = await client.post(
            "/api/snapshot/save",
            json={
                "parent_id": parent_id,
                "event_type": "sync",
                "players": [],
            },
        )
        assert resp.status_code in (200, 201)

    async def test_save_creates_branch_edge(self, client: Any, db_session: Any) -> None:
        """POST /api/snapshot/save must create a TimelineEdge with edge_type='branch'."""
        # Setup: Create parent snapshot with players and a child (so parent is not a leaf)
        parent_id = await make_snapshot_with_players(db_session, n=3)
        # Create a game event to make parent non-leaf (has a child)
        child_id = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)
        await create_game_edge(db_session, parent_id, child_id, 1)
        await db_session.commit()

        # Action: Save with modified player list (parent is now internal node, so new snapshot created)
        new_players = [
            {
                "nombre": f"ModifiedPlayer{i}",
                "is_new": False,
                "juegos_este_ano": i,
                "has_priority": True,
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

        parent_id = await make_root_manual_snapshot(
            db_session,
            players=[
                {
                    "nombre": "Juan",
                    "is_new": True,
                    "juegos_este_ano": 0,
                    "has_priority": False,
                    "partidas_deseadas": 1,
                    "partidas_gm": 0,
                }
            ],
        )
        await db_session.commit()

        # Verify setup: snapshot should have exactly 1 player
        players_before = await get_snapshot_players(db_session, parent_id)
        assert len(players_before) == 1
        assert players_before[0].nombre == "Juan"

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
                        "is_new": True,
                        "juegos_este_ano": 0,
                        "has_priority": False,
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

        # ── POST /api/snapshot/notion/fetch ───────────────────────────────────────────


class TestApiNotionFetch:
    async def test_notion_fetch_with_snapshot_names(self, client: Any, db_session: Any) -> None:
        """Regression test to ensure detect_similar_names doesn't throw KeyError on 'name'."""
        from datetime import datetime

        from backend.db.models import NotionCache

        # Add a notion cache entry first so it processes the loop
        nc = NotionCache(
            notion_id="notion-123",
            name="Real Notion Profile",
            is_new=True,
            last_updated=datetime.now(),
        )
        db_session.add(nc)
        await db_session.commit()

        resp = await client.post(
            "/api/snapshot/notion/fetch",
            json={"snapshot_names": ["Real Notion"]},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "players" in data
        assert "similar_names" in data
        assert len(data["similar_names"]) == 1
