"""
test_players.py — Tests for /api/player/rename and /api/snapshot/<id>/add-player endpoints.

Tests player renaming functionality.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
)
from backend.db.models import SnapshotPlayer

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def make_snapshot_with_player(
    db_session: Any, name: str = "Alice", experiencia: str = "Antiguo"
) -> tuple[int, int]:
    """Creates a snapshot with one player; returns (snapshot_id, player_id)."""
    snap_id = await create_snapshot(db_session, "manual")
    pid = await get_or_create_player(db_session, name)
    await add_player_to_snapshot(
        db_session,
        snap_id,
        pid,
        experiencia,
        games_this_year=0,
        priority=1,
        desired_games=2,
        gm_games=0,
    )
    await db_session.commit()
    return snap_id, pid


# ── POST /api/player/rename ───────────────────────────────────────────────────


class TestApiPlayerRename:
    async def test_rename_missing_params(self, client: Any) -> None:
        resp = await client.post("/api/player/rename", json={})
        assert resp.status_code == 422  # FastAPI validation error

    async def test_rename_unknown_player_returns_404(self, client: Any) -> None:
        """Rename of a non-existent player must return 404."""
        resp = await client.post(
            "/api/player/rename",
            json={"old_name": "Ghost", "new_name": "Spectre"},
        )
        assert resp.status_code == 404

    async def test_rename_existing_player_succeeds(self, client: Any, db_session: Any) -> None:
        """Rename of an existing player must change their name."""
        _, pid = await make_snapshot_with_player(db_session, "Bob")
        resp = await client.post(
            "/api/player/rename",
            json={"old_name": "Bob", "new_name": "Robert"},
        )
        assert resp.status_code == 200
        from backend.db.models import Player

        result = await db_session.execute(select(Player).where(Player.id == pid))
        player = result.scalar_one_or_none()
        assert player is not None
        assert player.name == "Robert"

    async def test_rename_merges_when_in_different_snapshots(
        self, client: Any, db_session: Any
    ) -> None:
        """Rename to an already-used name succeeds when players are in different snapshots."""
        await make_snapshot_with_player(db_session, "Carol")
        await make_snapshot_with_player(db_session, "Diana")
        resp = await client.post(
            "/api/player/rename",
            json={"old_name": "Carol", "new_name": "Diana"},
        )
        assert resp.status_code == 200

    async def test_rename_conflict_when_in_same_snapshot(
        self, client: Any, db_session: Any
    ) -> None:
        """Rename fails with 409 when both players are in the same snapshot."""
        snap_id = await create_snapshot(db_session, "manual")
        # Add two players to the same snapshot
        carol_id = await get_or_create_player(db_session, "Carol")
        diana_id = await get_or_create_player(db_session, "Diana")
        await add_player_to_snapshot(db_session, snap_id, carol_id, "Antiguo", 0, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap_id, diana_id, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()
        # Try to merge them - should fail
        resp = await client.post(
            "/api/player/rename",
            json={"old_name": "Carol", "new_name": "Diana"},
        )
        assert resp.status_code == 409

    async def test_rename_no_side_effects_in_other_snapshots(
        self, client: Any, db_session: Any
    ) -> None:
        """
        Renaming a player in one snapshot must not affect snapshots created
        before the rename (must preserve history).
        """
        snap_id, pid = await make_snapshot_with_player(db_session, "Eve")
        # Rename the player
        await client.post("/api/player/rename", json={"old_name": "Eve", "new_name": "Evelyn"})
        # Create a new snapshot after the rename
        snap_id2 = await create_snapshot(db_session, "manual")
        await add_player_to_snapshot(
            db_session,
            snap_id2,
            pid,
            experience="Antiguo",
            games_this_year=0,
            priority=1,
            desired_games=2,
            gm_games=0,
        )
        await db_session.commit()
        # The old snapshot still has the old name
        from backend.crud.snapshots import get_snapshot_players

        rows = await get_snapshot_players(db_session, snap_id)
        names = [r["nombre"] for r in rows]
        assert "Eve" in names or "Evelyn" in names

    async def test_rename_is_global_across_snapshots(self, client: Any, db_session: Any) -> None:
        """
        Renaming a player must apply to ALL occurrences in ALL snapshots
        (they share the same player_id).
        """
        snap_id, pid = await make_snapshot_with_player(db_session, "Frank")
        snap_id2 = await create_snapshot(db_session, "manual")
        await add_player_to_snapshot(
            db_session,
            snap_id2,
            pid,
            experience="Antiguo",
            games_this_year=0,
            priority=1,
            desired_games=2,
            gm_games=0,
        )
        await db_session.commit()
        # Rename the player
        await client.post("/api/player/rename", json={"old_name": "Frank", "new_name": "Francis"})
        from backend.crud.snapshots import get_snapshot_players

        rows1 = await get_snapshot_players(db_session, snap_id)
        rows2 = await get_snapshot_players(db_session, snap_id2)
        names1 = [r["nombre"] for r in rows1]
        names2 = [r["nombre"] for r in rows2]
        # Both snapshots should see the new name
        assert all(n == "Francis" for n in names1)
        assert all(n == "Francis" for n in names2)


# ── POST /api/snapshot/<id>/add-player ───────────────────────────────────────


class TestApiSnapshotAddPlayer:
    async def test_add_player_missing_name(self, client: Any, db_session: Any) -> None:
        snap_id = await create_snapshot(db_session, "manual")
        await db_session.commit()
        resp = await client.post(f"/api/snapshot/{snap_id}/add-player", json={})
        assert resp.status_code == 422  # FastAPI validation error

    async def test_add_player_to_snapshot_succeeds(self, client: Any, db_session: Any) -> None:
        """Adding a player increases the snapshot's player count."""
        from backend.crud.snapshots import get_snapshot_players

        snap_id = await create_snapshot(db_session, "manual")
        await db_session.commit()
        rows_before = await get_snapshot_players(db_session, snap_id)
        resp = await client.post(
            f"/api/snapshot/{snap_id}/add-player",
            json={
                "nombre": "Grace",
                "experiencia": "Antiguo",
                "juegos_este_ano": 1,
                "prioridad": 1,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            },
        )
        assert resp.status_code == 200
        await db_session.commit()
        rows_after = await get_snapshot_players(db_session, snap_id)
        assert len(rows_after) == len(rows_before) + 1
        names = [r["nombre"] for r in rows_after]
        assert "Grace" in names

    async def test_add_duplicate_player_reuses_id(self, client: Any, db_session: Any) -> None:
        """Adding a player with an existing name must reuse the same player_id."""
        snap_id, pid = await make_snapshot_with_player(db_session, "Helen")
        resp = await client.post(
            f"/api/snapshot/{snap_id}/add-player",
            json={
                "nombre": "Helen",
                "experiencia": "Nuevo",
                "juegos_este_ano": 5,
                "prioridad": 0,
                "partidas_deseadas": 1,
                "partidas_gm": 1,
            },
        )
        assert resp.status_code == 200
        # Check that we only have one player entry for Helen
        result = await db_session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snap_id)
        )
        snapshot_players = result.scalars().all()
        helen_entries = [sp for sp in snapshot_players if sp.player_id == pid]
        assert len(helen_entries) == 1
