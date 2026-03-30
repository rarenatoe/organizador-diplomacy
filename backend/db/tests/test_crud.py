"""
test_crud.py — Tests for async database CRUD operations.

Tests the async CRUD functions in backend/db/crud.py.
"""
from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from backend.db.crud import (
    add_mesa_player,
    add_player_to_snapshot,
    create_game_event,
    create_mesa,
    create_snapshot,
    create_sync_event,
    delete_snapshot_cascade,
    get_or_create_player,
    get_snapshot_players,
    rename_player,
    snapshots_have_same_roster,
)
from backend.db.models import Event, MesaPlayer, Player, Snapshot, SnapshotPlayer

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
        result = await db_session.execute(
            select(Player).where(Player.id == pid)
        )
        player = result.scalar_one()
        assert player.nombre == "Robert"

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
        await add_player_to_snapshot(
            db_session, snap_id, pid, "Antiguo", 0, 1, 2, 0
        )
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
        assert sp.experiencia == "Antiguo"

    async def test_get_snapshot_players(self, db_session: Any) -> None:
        """Getting snapshot players should return all players in the snapshot."""
        snap_id = await create_snapshot(db_session, "manual")
        for i in range(3):
            pid = await get_or_create_player(db_session, f"Player{i}")
            await add_player_to_snapshot(
                db_session, snap_id, pid, "Antiguo", i, 0, 1, 0
            )
        await db_session.commit()
        players = await get_snapshot_players(db_session, snap_id)
        assert len(players) == 3


# ── Event Tests ───────────────────────────────────────────────────────────────


class TestEventOperations:
    async def test_create_sync_event(self, db_session: Any) -> None:
        """Creating a sync event should link two snapshots."""
        snap1 = await create_snapshot(db_session, "notion_sync")
        snap2 = await create_snapshot(db_session, "notion_sync")
        await db_session.commit()
        event_id = await create_sync_event(db_session, snap1, snap2)
        await db_session.commit()
        assert event_id is not None
        result = await db_session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one()
        assert event.type == "sync"
        assert event.source_snapshot_id == snap1
        assert event.output_snapshot_id == snap2

    async def test_create_game_event(self, db_session: Any) -> None:
        """Creating a game event should create event and game_detail."""
        snap1 = await create_snapshot(db_session, "manual")
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()
        event_id = await create_game_event(db_session, snap1, snap2, 5, "draft_data")
        await db_session.commit()
        assert event_id is not None
        result = await db_session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one()
        assert event.type == "game"
        assert event.source_snapshot_id == snap1
        assert event.output_snapshot_id == snap2


# ── Mesa Tests ────────────────────────────────────────────────────────────────


class TestMesaOperations:
    async def test_create_mesa(self, db_session: Any) -> None:
        """Creating a mesa should assign an ID."""
        # First create a game event
        snap1 = await create_snapshot(db_session, "manual")
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()
        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        await db_session.commit()
        mesa_id = await create_mesa(db_session, event_id, 1)
        await db_session.commit()
        assert mesa_id is not None

    async def test_add_mesa_player(self, db_session: Any) -> None:
        """Adding a player to a mesa should create a MesaPlayer entry."""
        # Setup
        snap1 = await create_snapshot(db_session, "manual")
        snap2 = await create_snapshot(db_session, "organizar")
        pid = await get_or_create_player(db_session, "David")
        await db_session.commit()
        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        mesa_id = await create_mesa(db_session, event_id, 1)
        await db_session.commit()
        # Add player to mesa
        await add_mesa_player(db_session, mesa_id, pid, 1, "England")
        await db_session.commit()
        # Verify
        result = await db_session.execute(
            select(MesaPlayer).where(
                MesaPlayer.mesa_id == mesa_id,
                MesaPlayer.player_id == pid,
            )
        )
        mp = result.scalar_one()
        assert mp.pais == "England"


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
            {"nombre": "Alice", "experiencia": "Antiguo", "juegos_este_ano": 0, "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 0},
            {"nombre": "Bob", "experiencia": "Antiguo", "juegos_este_ano": 0, "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 0},
            {"nombre": "Charlie", "experiencia": "Antiguo", "juegos_este_ano": 0, "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 0},
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
            {"nombre": "Bob", "experiencia": "Antiguo", "juegos_este_ano": 0, "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 0},
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
        result = await db_session.execute(
            select(Snapshot).where(Snapshot.id == snap_id)
        )
        assert result.scalar_one_or_none() is None
        # Verify snapshot_players are gone
        result = await db_session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snap_id)
        )
        assert result.scalar_one_or_none() is None
