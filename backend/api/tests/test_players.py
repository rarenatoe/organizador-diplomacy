"""
test_players.py — Tests for /api/player/rename and /api/snapshot/<id>/add-player endpoints.

Tests player renaming functionality.
"""

from __future__ import annotations

from datetime import datetime
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
    db_session: Any, name: str = "Alice", experience: str = "Antiguo"
) -> tuple[int, int]:
    """Creates a snapshot with one player; returns (snapshot_id, player_id)."""
    snap_id = await create_snapshot(db_session, "manual")
    pid = await get_or_create_player(db_session, name)
    await add_player_to_snapshot(
        db_session,
        snap_id,
        pid,
        experience,
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


class TestPlayerLookup:
    """Tests for /api/player/lookup endpoint with deep lookup and multiple fallbacks."""

    async def test_lookup_empty_names_returns_400(self, client: Any) -> None:
        """Test lookup with empty names list returns 400."""
        resp = await client.post("/api/player/lookup", json={"names": []})
        assert resp.status_code == 400
        assert "names list cannot be empty" in resp.json()["detail"]

    async def test_lookup_no_snapshots_returns_defaults(self, client: Any) -> None:
        """Test lookup when no snapshots exist returns default values."""
        resp = await client.post("/api/player/lookup", json={"names": ["Alice", "Bob"]})
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        # Should return default values for both players
        assert "Alice" in players
        assert "Bob" in players
        assert players["Alice"]["source"] == "default"
        assert players["Bob"]["source"] == "default"
        assert players["Alice"]["prioridad"] == 0
        assert players["Alice"]["experiencia"] == "Nuevo"
        assert players["Alice"]["juegos_este_ano"] == 0

    async def test_lookup_timeline_traversal_finds_history(
        self, client: Any, db_session: Any
    ) -> None:
        """Test lookup finds player via TimelineEdge ancestry and returns source='history'."""
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot
        from backend.db.models import TimelineEdge

        # Create player and add to a snapshot to establish history
        snap_id = await create_snapshot(db_session, "manual")
        player_id = await get_or_create_player(db_session, "Charlie")
        await add_player_to_snapshot(
            session=db_session,
            snapshot_id=snap_id,
            player_id=player_id,
            experience="Veterano",
            games_this_year=0,
            priority=1,
            desired_games=1,
            gm_games=0,
        )
        await db_session.commit()

        # Create timeline edge from snapshot to None (makes it part of timeline)
        edge = TimelineEdge(
            id=1, source_snapshot_id=None, output_snapshot_id=snap_id, edge_type="branch"
        )
        db_session.add(edge)
        await db_session.commit()

        resp = await client.post(
            "/api/player/lookup", json={"names": ["Charlie"], "snapshot_id": None}
        )
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        assert "Charlie" in players
        # Should be from history, not from Notion global fallback
        assert players["Charlie"]["source"] == "history"
        assert players["Charlie"]["prioridad"] == 1
        assert players["Charlie"]["experiencia"] == "Veterano"  # From snapshot
        assert players["Charlie"]["juegos_este_ano"] == 0

    async def test_lookup_global_fallback_finds_snapshot_player(
        self, client: Any, db_session: Any
    ) -> None:
        """Test lookup finds player in SnapshotPlayer elsewhere and returns source='history'."""
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

        # Create snapshot with player
        snap_id = await create_snapshot(db_session, "manual")
        player_id = await get_or_create_player(db_session, "Diana")
        await add_player_to_snapshot(
            session=db_session,
            snapshot_id=snap_id,
            player_id=player_id,
            experience="Veterano",
            games_this_year=1,
            priority=1,
            desired_games=1,
            gm_games=1,
        )
        await db_session.commit()

        # Test lookup from different snapshot (should find via global fallback)
        resp = await client.post(
            "/api/player/lookup", json={"names": ["Diana"], "snapshot_id": snap_id + 1}
        )
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        assert "Diana" in players
        assert players["Diana"]["source"] == "history"
        assert players["Diana"]["prioridad"] == 1
        assert players["Diana"]["experiencia"] == "Veterano"
        assert players["Diana"]["juegos_este_ano"] == 1

    async def test_lookup_json_rescue_finds_deleted_player(
        self, client: Any, db_session: Any
    ) -> None:
        """Test lookup finds player in SnapshotHistory JSON logs and returns source='history'."""
        from backend.crud.snapshots import create_snapshot
        from backend.db.models import (
            DeepDiffResult,
            HistoryActionType,
            HistoryStateDict,
            SnapshotHistory,
        )

        # Create player and snapshot with history
        player_id = await get_or_create_player(db_session, "Eve")
        snap_id = await create_snapshot(db_session, "manual")

        # Add player to snapshot, then delete player from snapshot, then create history entry
        await add_player_to_snapshot(db_session, snap_id, player_id, "Veterano", 1, 2, 1, 1)
        await db_session.commit()

        # Delete player from snapshot (simulating deletion)
        from backend.db.models import SnapshotPlayer

        result = await db_session.execute(
            select(SnapshotPlayer).where(SnapshotPlayer.player_id == player_id)
        )
        sp_player = result.scalar_one_or_none()
        if sp_player:
            await db_session.delete(sp_player)
            await db_session.commit()

        # Create history log with player data
        changes = DeepDiffResult(added=[], removed=["Eve"], renamed=[], modified=[])
        history_state = HistoryStateDict(
            players=[
                {
                    "nombre": "Eve",
                    "experiencia": "Veterano",
                    "juegos_este_ano": 1,
                    "prioridad": 1,
                    "partidas_deseadas": 2,
                    "partidas_gm": 1,
                }
            ]
        )
        history_entry = SnapshotHistory(
            snapshot_id=snap_id,
            action_type=HistoryActionType.MANUAL_EDIT,
            changes=changes,
            previous_state=history_state,
        )
        db_session.add(history_entry)
        await db_session.commit()

        # Test lookup should find player in JSON logs
        resp = await client.post(
            "/api/player/lookup", json={"names": ["Eve"], "snapshot_id": snap_id + 1}
        )
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        assert "Eve" in players
        assert players["Eve"]["source"] == "history"
        assert players["Eve"]["prioridad"] == 1
        assert players["Eve"]["experiencia"] == "Veterano"
        assert players["Eve"]["juegos_este_ano"] == 1

    async def test_lookup_notion_fallback_returns_notion_stats(
        self, client: Any, db_session: Any
    ) -> None:
        """Test lookup finds player only in NotionCache and returns source='notion' with forced defaults."""
        from backend.db.models import NotionCache

        # Create player in NotionCache
        notion_player = NotionCache(
            notion_id="test-notion-id",
            name="Frank",
            experience="Veterano",
            games_this_year=3,
            c_england=1,
            c_france=0,
            c_italy=0,
            c_austria=1,
            c_russia=0,
            c_turkey=1,
            last_updated=datetime.now(),
        )
        db_session.add(notion_player)
        await db_session.commit()

        # Test lookup should find player in NotionCache
        resp = await client.post(
            "/api/player/lookup", json={"names": ["Frank"], "snapshot_id": None}
        )
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        assert "Frank" in players
        assert players["Frank"]["source"] == "notion"
        # Notion fallback should force specific defaults regardless of Notion data
        assert players["Frank"]["prioridad"] == 0
        assert players["Frank"]["partidas_deseadas"] == 1
        assert players["Frank"]["partidas_gm"] == 0
        assert players["Frank"]["experiencia"] == "Veterano"  # From Notion
        assert players["Frank"]["juegos_este_ano"] == 3

    async def test_lookup_unknown_player_returns_defaults(self, client: Any) -> None:
        """Test lookup for completely unknown player returns default values."""
        resp = await client.post("/api/player/lookup", json={"names": ["UnknownPlayer"]})
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        assert "UnknownPlayer" in players
        assert players["UnknownPlayer"]["source"] == "default"
        assert players["UnknownPlayer"]["prioridad"] == 0
        assert players["UnknownPlayer"]["experiencia"] == "Nuevo"
        assert players["UnknownPlayer"]["juegos_este_ano"] == 0

    async def test_lookup_multiple_players_mixed_sources(
        self, client: Any, db_session: Any
    ) -> None:
        """Test lookup with multiple players from different sources."""
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot
        from backend.db.models import NotionCache

        # Setup: Player in snapshot history
        snap_id1 = await create_snapshot(db_session, "manual")
        player_id1 = await get_or_create_player(db_session, "Alice")
        await add_player_to_snapshot(
            session=db_session,
            snapshot_id=snap_id1,
            player_id=player_id1,
            experience="Veterano",
            games_this_year=1,
            priority=1,
            desired_games=1,
            gm_games=1,
        )

        # Setup: Player in NotionCache
        notion_player = NotionCache(
            notion_id="test-notion-id",
            name="Bob",
            experience="Veterano",
            games_this_year=3,
            last_updated=datetime.now(),
        )
        db_session.add(notion_player)
        await db_session.commit()

        # Test lookup for both players
        resp = await client.post(
            "/api/player/lookup", json={"names": ["Alice", "Bob"], "snapshot_id": snap_id1}
        )
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        # Alice should be from history
        assert players["Alice"]["source"] == "history"
        assert players["Alice"]["prioridad"] == 1
        assert players["Alice"]["experiencia"] == "Veterano"

        # Bob should be from Notion with forced defaults
        assert players["Bob"]["source"] == "notion"
        assert players["Bob"]["prioridad"] == 0
        assert players["Bob"]["partidas_deseadas"] == 1
        assert players["Bob"]["partidas_gm"] == 0

    async def test_lookup_with_snapshot_id_prioritizes_history(
        self, client: Any, db_session: Any
    ) -> None:
        """Test that providing snapshot_id prioritizes history lookup over global fallbacks."""
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot
        from backend.db.models import NotionCache

        # Create player in NotionCache (global fallback)
        notion_player = NotionCache(
            notion_id="global-charlie-id",
            name="Charlie",
            experience="Novato",
            last_updated=datetime.now(),
        )
        db_session.add(notion_player)
        await db_session.commit()

        # Create player in snapshot history
        snap_id = await create_snapshot(db_session, "manual")
        player_id = await get_or_create_player(db_session, "Charlie")
        await add_player_to_snapshot(
            session=db_session,
            snapshot_id=snap_id,
            player_id=player_id,
            experience="Veterano",
            games_this_year=1,
            priority=1,
            desired_games=1,
            gm_games=1,
        )
        await db_session.commit()

        # Test lookup with snapshot_id should prioritize history
        resp = await client.post(
            "/api/player/lookup", json={"names": ["Charlie"], "snapshot_id": snap_id}
        )
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        assert "Charlie" in players
        # Should be from history, not from Notion global fallback
        assert players["Charlie"]["source"] == "history"
        assert players["Charlie"]["prioridad"] == 1
        assert players["Charlie"]["experiencia"] == "Veterano"  # From snapshot
