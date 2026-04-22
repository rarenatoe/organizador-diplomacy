"""
test_players.py - Tests for player API behavior.

Tests player renaming and lookup functionality.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from backend.api.models.snapshots import DeepDiffResult, HistoryState, PlayerData
from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
)
from backend.db.models import (
    NotionCache,
    Player,
    SnapshotHistory,
    SnapshotSource,
    TimelineEdge,
)

if TYPE_CHECKING:
    from typing import Any

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def make_snapshot_with_player(db_session: Any, name: str = "Alice") -> tuple[int, int]:
    """Creates a snapshot with one player; returns (snapshot_id, player_id)."""
    snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)
    pid = await get_or_create_player(db_session, name)
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
        snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)
        # Add two players to the same snapshot
        carol_id = await get_or_create_player(db_session, "Carol")
        diana_id = await get_or_create_player(db_session, "Diana")
        await add_player_to_snapshot(
            db_session, snap_id, carol_id, 0, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, snap_id, diana_id, 0, 2, 0, has_priority=True, is_new=False
        )
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
        snap_id2 = await create_snapshot(db_session, SnapshotSource.MANUAL)
        await add_player_to_snapshot(
            db_session,
            snap_id2,
            pid,
            games_this_year=0,
            desired_games=2,
            gm_games=0,
            has_priority=True,
            is_new=False,
        )
        await db_session.commit()
        # The old snapshot still has the old name
        from backend.crud.snapshots import get_snapshot_players

        rows = await get_snapshot_players(db_session, snap_id)
        names = [r.nombre for r in rows]
        assert "Eve" in names or "Evelyn" in names

    async def test_rename_is_global_across_snapshots(self, client: Any, db_session: Any) -> None:
        """
        Renaming a player must apply to ALL occurrences in ALL snapshots
        (they share the same player_id).
        """
        snap_id, pid = await make_snapshot_with_player(db_session, "Frank")
        snap_id2 = await create_snapshot(db_session, SnapshotSource.MANUAL)
        await add_player_to_snapshot(
            db_session,
            snap_id2,
            pid,
            games_this_year=0,
            desired_games=2,
            gm_games=0,
            has_priority=True,
            is_new=False,
        )
        await db_session.commit()
        # Rename the player
        await client.post("/api/player/rename", json={"old_name": "Frank", "new_name": "Francis"})
        from backend.crud.snapshots import get_snapshot_players

        rows1 = await get_snapshot_players(db_session, snap_id)
        rows2 = await get_snapshot_players(db_session, snap_id2)
        names1 = [r.nombre for r in rows1]
        names2 = [r.nombre for r in rows2]
        # Both snapshots should see the new name
        assert all(n == "Francis" for n in names1)
        assert all(n == "Francis" for n in names2)


class TestPlayerLookup:
    """Consolidated tests for /api/player/lookup and lookup_player_history logic."""

    async def test_lookup_missing_name_returns_422(self, client: Any) -> None:
        resp = await client.post("/api/player/lookup", json={})
        assert resp.status_code == 422

    async def test_lookup_no_data_returns_default(self, client: Any) -> None:
        """Verify the 'default' source when absolutely nothing is found."""
        resp = await client.post("/api/player/lookup", json={"name": "New Soul"})
        data = resp.json()["player"]
        assert data["source"] == "default"
        assert data["is_new"] is True
        assert data.get("notion_id") is None

    async def test_lookup_prioritizes_provided_notion_id(
        self, client: Any, db_session: Any
    ) -> None:
        """
        Target: Refactored Notion logic.
        Ensures 'notion_id' in request overrides everything else (Vincular Solo case).
        """
        nc = NotionCache(
            notion_id="notion-999",
            name="Real Name",
            is_new=False,
            games_this_year=5,
            last_updated=datetime.now(),
        )
        db_session.add(nc)
        await db_session.commit()

        resp = await client.post(
            "/api/player/lookup", json={"name": "Typo Name", "notion_id": "notion-999"}
        )
        player = resp.json()["player"]
        assert player["notion_id"] == "notion-999"
        assert player["notion_name"] == "Real Name"
        assert player["source"] == "notion"

    async def test_lookup_finds_notion_via_local_player_link(
        self, client: Any, db_session: Any
    ) -> None:
        """
        Target: Refactored logic 'elif player and player.notion_id'.
        If a player exists locally and has a notion_id, use it to get stats.
        """
        nc = NotionCache(
            notion_id="notion-777",
            name="Linked Notion",
            is_new=False,
            games_this_year=10,
            last_updated=datetime.now(),
        )
        db_session.add(nc)
        # Create a local player already linked to that ID
        p_id = await get_or_create_player(db_session, "Local Charlie")
        from sqlalchemy import update

        await db_session.execute(
            update(Player).where(Player.id == p_id).values(notion_id="notion-777")
        )
        await db_session.commit()

        resp = await client.post("/api/player/lookup", json={"name": "Local Charlie"})
        player = resp.json()["player"]
        assert player["notion_id"] == "notion-777"
        assert player["juegos_este_ano"] == 10

    async def test_lookup_notion_search_is_case_insensitive(
        self, client: Any, db_session: Any
    ) -> None:
        """Target: 'func.lower(NotionCache.name) == name.lower()'."""
        nc = NotionCache(
            notion_id="notion-123", name="Case Sensitive", is_new=True, last_updated=datetime.now()
        )
        db_session.add(nc)
        await db_session.commit()

        resp = await client.post("/api/player/lookup", json={"name": "caSE senSITive"})
        player = resp.json()["player"]
        assert player["notion_id"] == "notion-123"

    async def test_lookup_timeline_traversal(self, client: Any, db_session: Any) -> None:
        """Ensures we can walk back through TimelineEdges to find history."""
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

        s1 = await create_snapshot(db_session, SnapshotSource.MANUAL)
        s2 = await create_snapshot(db_session, SnapshotSource.MANUAL)  # The 'current' one
        p_id = await get_or_create_player(db_session, "Walker")

        # Add player to s1 (the past)
        await add_player_to_snapshot(db_session, s1, p_id, 2, 1, 0, has_priority=True, is_new=False)
        # Link s2 -> s1
        edge = TimelineEdge(id=1, source_snapshot_id=s1, output_snapshot_id=s2, edge_type="branch")
        db_session.add(edge)
        await db_session.commit()

        resp = await client.post("/api/player/lookup", json={"name": "Walker", "snapshot_id": s2})
        player = resp.json()["player"]
        assert player["source"] == "history"
        assert player["juegos_este_ano"] == 2
        assert player["has_priority"] is True

    async def test_lookup_global_fallback(self, client: Any, db_session: Any) -> None:
        """If not in timeline, find the most recent SnapshotPlayer record globally."""
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

        old_snap = await create_snapshot(db_session, SnapshotSource.MANUAL)
        p_id = await get_or_create_player(db_session, "Globalist")
        await add_player_to_snapshot(
            db_session, old_snap, p_id, 5, 1, 0, has_priority=False, is_new=False
        )
        await db_session.commit()

        # Lookup with a completely unrelated snapshot_id
        resp = await client.post(
            "/api/player/lookup", json={"name": "Globalist", "snapshot_id": 999}
        )
        player = resp.json()["player"]
        assert player["source"] == "history"
        assert player["juegos_este_ano"] == 5

    async def test_lookup_json_logs_rescue(self, client: Any, db_session: Any) -> None:
        """Test the 'Fallback 2': searching through SnapshotHistory.previous_state."""
        history_state = HistoryState(
            players=[
                PlayerData(
                    nombre="Ghost",
                    is_new=False,
                    juegos_este_ano=8,
                    has_priority=True,
                    partidas_deseadas=1,
                    partidas_gm=0,
                    notion_id=None,
                    notion_name=None,
                    c_england=0,
                    c_france=0,
                    c_germany=0,
                    c_italy=0,
                    c_austria=0,
                    c_russia=0,
                    c_turkey=0,
                    alias=None,
                )
            ]
        )
        history_entry = SnapshotHistory(
            snapshot_id=1,
            action_type=SnapshotSource.MANUAL_EDIT,
            changes=DeepDiffResult(added=[], removed=[], renamed=[], modified=[]).model_dump(),
            previous_state=history_state.model_dump(),
        )
        db_session.add(history_entry)
        await db_session.commit()

        resp = await client.post("/api/player/lookup", json={"name": "Ghost"})
        player = resp.json()["player"]
        assert player["source"] == "history"
        assert player["juegos_este_ano"] == 8
        assert player["has_priority"] is True
