"""
test_crud.py — Tests for async database CRUD operations.

Tests the async CRUD functions in backend/db/crud.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from backend.crud.chain import (
    create_branch_edge,
    create_game_edge,
    squash_linear_branch,
)
from backend.crud.games import (
    add_table_player,
    create_game_table,
)
from backend.crud.players import (
    get_or_create_player,
    rename_player,
)
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
    delete_snapshot_cascade,
    get_snapshot_players,
    snapshots_have_same_roster,
)
from backend.db.models import (
    Player,
    Snapshot,
    SnapshotPlayer,
    TablePlayer,
    TimelineEdge,
)

pytestmark = pytest.mark.asyncio


# ── Player Tests ─────────────────────────────────────────────────────────────


class TestPlayerOperations:
    async def test_get_or_create_player_creates_new(self, db_session: Any) -> None:
        """Creating a new player should assign an ID."""
        pid = await get_or_create_player(db_session, "TestPlayer")
        await db_session.commit()
        assert pid is not None
        assert isinstance(pid, int)

    async def test_get_or_create_player_returns_existing(self, db_session: Any) -> None:
        """Getting an existing player should return the same ID."""
        pid1 = await get_or_create_player(db_session, "Alice")
        await db_session.commit()
        pid2 = await get_or_create_player(db_session, "Alice")
        await db_session.commit()
        assert pid1 == pid2

    async def test_rename_player(self, db_session: Any) -> None:
        """Renaming a player should change their name."""
        pid = await get_or_create_player(db_session, "Bob")
        await db_session.commit()
        success = await rename_player(db_session, "Bob", "Robert")
        await db_session.commit()
        assert success is True
        result = await db_session.execute(select(Player).where(Player.id == pid))
        player = result.scalar_one()
        assert player.name == "Robert"

    async def test_rename_player_not_found(self, db_session: Any) -> None:
        """Renaming a non-existent player should return False."""
        success = await rename_player(db_session, "Ghost", "Spirit")
        assert success is False


# ── Snapshot Tests ────────────────────────────────────────────────────────────


class TestSnapshotOperations:
    async def test_create_snapshot(self, db_session: Any) -> None:
        """Creating a snapshot should assign an ID and timestamp."""
        snap_id = await create_snapshot(db_session, "manual")
        await db_session.commit()
        assert snap_id is not None
        assert isinstance(snap_id, int)

    async def test_add_player_to_snapshot(self, db_session: Any) -> None:
        """Adding a player to a snapshot should create a SnapshotPlayer entry."""
        snap_id = await create_snapshot(db_session, "manual")
        pid = await get_or_create_player(db_session, "Charlie")
        await db_session.commit()
        await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()
        # Verify
        result = await db_session.execute(
            select(SnapshotPlayer).where(
                SnapshotPlayer.snapshot_id == snap_id,
                SnapshotPlayer.player_id == pid,
            )
        )
        sp = result.scalar_one()
        assert sp is not None
        assert sp.experience == "Antiguo"

    async def test_get_snapshot_players(self, db_session: Any) -> None:
        """Getting snapshot players should return all players in the snapshot."""
        snap_id = await create_snapshot(db_session, "manual")
        for i in range(3):
            pid = await get_or_create_player(db_session, f"Player{i}")
            await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", i, 0, 1, 0)
        await db_session.commit()
        players = await get_snapshot_players(db_session, snap_id)
        assert len(players) == 3


# ── TimelineEdge Tests ───────────────────────────────────────────────────────


class TestTimelineEdgeOperations:
    async def test_create_branch_edge(self, db_session: Any) -> None:
        """Creating a sync event should link two snapshots."""
        snap1 = await create_snapshot(db_session, "notion_sync")
        snap2 = await create_snapshot(db_session, "notion_sync")
        await db_session.commit()
        event_id = await create_branch_edge(db_session, snap1, snap2)
        await db_session.commit()
        assert event_id is not None
        result = await db_session.execute(select(TimelineEdge).where(TimelineEdge.id == event_id))
        event = result.scalar_one()
        assert event.edge_type == "branch"
        assert event.source_snapshot_id == snap1
        assert event.output_snapshot_id == snap2

    async def test_create_game_edge(self, db_session: Any) -> None:
        """Creating a game event should create event and game_detail."""
        snap1 = await create_snapshot(db_session, "manual")
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()
        event_id = await create_game_edge(db_session, snap1, snap2, 5)
        await db_session.commit()
        assert event_id is not None
        result = await db_session.execute(select(TimelineEdge).where(TimelineEdge.id == event_id))
        event = result.scalar_one()
        assert event.edge_type == "game"
        assert event.source_snapshot_id == snap1
        assert event.output_snapshot_id == snap2


# ── GameTable Tests ──────────────────────────────────────────────────────────


class TestGameTableOperations:
    async def test_create_game_table(self, db_session: Any) -> None:
        """Creating a mesa should assign an ID."""
        # First create a game event
        snap1 = await create_snapshot(db_session, "manual")
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()
        event_id = await create_game_edge(db_session, snap1, snap2, 1)
        await db_session.commit()
        mesa_id = await create_game_table(db_session, event_id, 1)
        await db_session.commit()
        assert mesa_id is not None

    async def test_add_table_player(self, db_session: Any) -> None:
        """Adding a player to a mesa should create a TablePlayer entry."""
        # Setup
        snap1 = await create_snapshot(db_session, "manual")
        snap2 = await create_snapshot(db_session, "organizar")
        pid = await get_or_create_player(db_session, "David")
        await db_session.commit()
        event_id = await create_game_edge(db_session, snap1, snap2, 1)
        mesa_id = await create_game_table(db_session, event_id, 1)
        await db_session.commit()
        # Add player to mesa
        await add_table_player(db_session, mesa_id, pid, 1, "England")
        await db_session.commit()
        # Verify
        result = await db_session.execute(
            select(TablePlayer).where(
                TablePlayer.table_id == mesa_id,
                TablePlayer.player_id == pid,
            )
        )
        mp = result.scalar_one()
        assert mp.country == "England"


# ── Roster Comparison Tests ───────────────────────────────────────────────────


class TestRosterComparison:
    async def test_same_roster_returns_true(self, db_session: Any) -> None:
        """Snapshot roster matching Notion data should return True."""
        snap_id = await create_snapshot(db_session, "manual")
        for name in ["Alice", "Bob", "Charlie"]:
            pid = await get_or_create_player(db_session, name)
            await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()
        # Build matching notion rows
        notion_rows = [
            {
                "nombre": "Alice",
                "experiencia": "Antiguo",
                "juegos_este_ano": 0,
                "prioridad": 1,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            },
            {
                "nombre": "Bob",
                "experiencia": "Antiguo",
                "juegos_este_ano": 0,
                "prioridad": 1,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            },
            {
                "nombre": "Charlie",
                "experiencia": "Antiguo",
                "juegos_este_ano": 0,
                "prioridad": 1,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            },
        ]
        # Should match
        same = await snapshots_have_same_roster(db_session, snap_id, notion_rows)
        assert same is True

    async def test_different_roster_returns_false(self, db_session: Any) -> None:
        """Snapshot roster different from Notion data should return False."""
        snap_id = await create_snapshot(db_session, "manual")
        pid = await get_or_create_player(db_session, "Alice")
        await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()
        # Different notion rows
        notion_rows = [
            {
                "nombre": "Bob",
                "experiencia": "Antiguo",
                "juegos_este_ano": 0,
                "prioridad": 1,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            },
        ]
        # Should not match
        same = await snapshots_have_same_roster(db_session, snap_id, notion_rows)
        assert same is False


# ── Cascade Delete Tests ────────────────────────────────────────────────────


class TestCascadeDelete:
    async def test_delete_snapshot_cascade(self, db_session: Any) -> None:
        """Deleting a snapshot should cascade to related entities."""
        snap_id = await create_snapshot(db_session, "manual")
        pid = await get_or_create_player(db_session, "Test")
        await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()
        # Delete
        await delete_snapshot_cascade(db_session, snap_id)
        await db_session.commit()
        # Verify snapshot is gone
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_id))
        assert result.scalar_one_or_none() is None
        # Verify snapshot_players are gone
        result = await db_session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snap_id)
        )
        assert result.scalar_one_or_none() is None


# ── Linear Branch Squashing Tests ─────────────────────────────────────────────


class TestLinearBranchSquashing:
    async def test_squash_single_non_game_edge(self, db_session: Any) -> None:
        """Squashing a snapshot with one non-game child should absorb the child."""
        # Setup: A -> branch -> B
        snap_a = await create_snapshot(db_session, "notion_sync")
        snap_b = await create_snapshot(db_session, "manual")

        # Add players to both snapshots
        pid_a = await get_or_create_player(db_session, "PlayerA")
        await add_player_to_snapshot(db_session, snap_a, pid_a, "Antiguo", 5, 1, 2, 0)

        pid_b1 = await get_or_create_player(db_session, "PlayerB1")
        pid_b2 = await get_or_create_player(db_session, "PlayerB2")
        await add_player_to_snapshot(db_session, snap_b, pid_b1, "Nuevo", 2, 1, 1, 0)
        await add_player_to_snapshot(db_session, snap_b, pid_b2, "Antiguo", 3, 1, 2, 0)

        # Create branch edge A -> B
        await create_branch_edge(db_session, snap_a, snap_b)
        await db_session.commit()

        # Get B's source and timestamp before squashing
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        snap_b_obj = result.scalar_one()
        b_source = snap_b_obj.source
        b_timestamp = snap_b_obj.created_at

        # Action: Squash A
        await squash_linear_branch(db_session, snap_a)
        await db_session.commit()
        db_session.expire_all()

        # Assert 1: Snapshot B is gone
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is None

        # Assert 2: Snapshot A still exists
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        snap_a_obj = result.scalar_one()
        assert snap_a_obj is not None

        # Assert 3: A's roster is now B's roster
        players_a = await get_snapshot_players(db_session, snap_a)
        assert len(players_a) == 2
        player_names = {p["nombre"] for p in players_a}
        assert player_names == {"PlayerB1", "PlayerB2"}

        # Assert 4: A inherited B's source and timestamp
        assert snap_a_obj.source == b_source
        assert snap_a_obj.created_at == b_timestamp

        # Assert 5: A has no outgoing edges
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snap_a)
        )
        assert len(result.scalars().all()) == 0

    async def test_squash_does_not_affect_game_edges(self, db_session: Any) -> None:
        """Squashing should not affect snapshots with game edges."""
        # Setup: A -> game -> B
        snap_a = await create_snapshot(db_session, "notion_sync")
        snap_b = await create_snapshot(db_session, "organizar")

        pid = await get_or_create_player(db_session, "Test")
        await add_player_to_snapshot(db_session, snap_a, pid, "Antiguo", 0, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap_b, pid, "Antiguo", 1, 0, 2, 0)

        # Create game edge A -> B
        await create_game_edge(db_session, snap_a, snap_b, 1)
        await db_session.commit()

        # Action: Try to squash A (should do nothing because edge is a game)
        await squash_linear_branch(db_session, snap_a)
        await db_session.commit()

        # Assert: Both snapshots still exist
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        assert result.scalar_one_or_none() is not None

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is not None

    async def test_squash_does_not_affect_multiple_edges(self, db_session: Any) -> None:
        """Squashing should not affect snapshots with multiple outgoing edges."""
        # Setup: A -> branch -> B
        #        A -> branch -> C
        snap_a = await create_snapshot(db_session, "notion_sync")
        snap_b = await create_snapshot(db_session, "manual")
        snap_c = await create_snapshot(db_session, "manual")

        pid = await get_or_create_player(db_session, "Test")
        await add_player_to_snapshot(db_session, snap_a, pid, "Antiguo", 0, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap_b, pid, "Antiguo", 1, 0, 2, 0)
        await add_player_to_snapshot(db_session, snap_c, pid, "Antiguo", 2, 0, 2, 0)

        # Create two branch edges from A
        await create_branch_edge(db_session, snap_a, snap_b)
        await create_branch_edge(db_session, snap_a, snap_c)
        await db_session.commit()

        # Action: Try to squash A (should do nothing because it has 2 edges)
        await squash_linear_branch(db_session, snap_a)
        await db_session.commit()

        # Assert: All snapshots still exist
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        assert result.scalar_one_or_none() is not None

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is not None

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_c))
        assert result.scalar_one_or_none() is not None

    async def test_squash_recursive_chain(self, db_session: Any) -> None:
        """Squashing should recursively collapse linear chains A -> B -> C -> A."""
        # Setup: A -> branch -> B -> branch -> C
        snap_a = await create_snapshot(db_session, "notion_sync")
        snap_b = await create_snapshot(db_session, "manual")
        snap_c = await create_snapshot(db_session, "manual")

        # Only add players to C (final state)
        pid = await get_or_create_player(db_session, "FinalPlayer")
        await add_player_to_snapshot(db_session, snap_a, pid, "Antiguo", 0, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap_b, pid, "Antiguo", 1, 0, 2, 0)
        await add_player_to_snapshot(db_session, snap_c, pid, "Antiguo", 2, 0, 2, 0)

        # Create chain A -> B -> C
        await create_branch_edge(db_session, snap_a, snap_b)
        await create_branch_edge(db_session, snap_b, snap_c)
        await db_session.commit()

        # Get C's source before squashing
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_c))
        snap_c_obj = result.scalar_one()
        c_source = snap_c_obj.source

        # Action: Squash A (should recursively collapse B and C into A)
        await squash_linear_branch(db_session, snap_a)
        await db_session.commit()
        db_session.expire_all()

        # Assert 1: Only A remains
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        assert result.scalar_one_or_none() is not None

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is None

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_c))
        assert result.scalar_one_or_none() is None

        # Assert 2: A has C's final roster
        players_a = await get_snapshot_players(db_session, snap_a)
        assert players_a[0]["juegos_este_ano"] == 2

        # Assert 3: A inherited the final source
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        snap_a_obj = result.scalar_one()
        assert snap_a_obj.source == c_source
