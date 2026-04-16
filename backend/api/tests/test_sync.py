"""
test_sync.py — Tests for /api/run/notion_sync and /api/notion/force_refresh endpoints.

Tests the sync daemon and Notion cache functionality.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


# ── Shared Test Fixtures ─────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="module")
async def background_test_engine():
    """Create a shared async engine for all background sync tests."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from backend.db.models import Base

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Initialize database schema once for the entire module
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Clean up after all tests in the module
    await test_engine.dispose()


# ── POST /api/run/notion_sync ─────────────────────────────────────────────────


class TestApiRunNotionSync:
    async def test_notion_sync_starts_background_task(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """The notion_sync endpoint should start a background task and return immediately."""
        with patch(
            "backend.api.routers.sync.run_notion_sync_background",
            new_callable=AsyncMock,
        ) as mock_run:
            merges_payload = {"Renato": {"to": "Renato Alegre", "action": "merge_notion"}}
            resp = await client.post("/api/run/notion_sync", json={"merges": merges_payload})
            assert resp.status_code == 200
            data = resp.json()
            assert "sync_id" in data or "success" in data
            # Verify background task was scheduled with correct merges payload
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("merges") == merges_payload

    async def test_notion_sync_returns_error_on_exception(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Background tasks are added successfully even if they will fail later."""
        with patch(
            "backend.sync.notion_sync.run_notion_sync_background",
            side_effect=Exception("Sync failed"),
        ):
            resp = await client.post("/api/run/notion_sync", json={})
            # Background task error is caught and logged, endpoint returns success
            assert resp.status_code == 200


# ── POST /api/snapshot/notion/fetch ───────────────────────────────────────────


class TestApiNotionPlayers:
    async def test_get_notion_players_cached(self, client: Any, db_session: Any) -> None:
        """Should return cached Notion players if available."""
        # Insert test data into notion_cache
        from datetime import datetime

        from backend.db.models import NotionCache

        cache_entry = NotionCache(
            notion_id="test_id_1",
            name="Test Player",
            experience="Antiguo",
            games_this_year=5,
            c_england=1,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=0,
            last_updated=datetime(2026, 3, 30, 12, 0, 0),
        )
        db_session.add(cache_entry)
        await db_session.commit()

        resp = await client.post("/api/snapshot/notion/fetch", json={"snapshot_id": None})
        assert resp.status_code == 200
        data = resp.json()
        assert "players" in data
        assert len(data["players"]) > 0

    async def test_get_notion_players_no_cache(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Should handle case when cache is empty."""
        resp = await client.post("/api/snapshot/notion/fetch", json={"snapshot_id": None})
        assert resp.status_code == 200
        data = resp.json()
        assert "players" in data
        # Empty cache should return empty list
        assert data["players"] == []

    async def test_notion_fetch_with_similar_names(self, client: Any, db_session: Any) -> None:
        """
        Regression test: detect_similar_names must handle dict input correctly.
        Previously crashed when receiving a list instead of a dict.
        """
        from datetime import datetime

        from backend.db.models import NotionCache

        # Insert mock cache entry
        cache_entry = NotionCache(
            notion_id="test_id_renato",
            name="Renato Alegre",
            experience="Antiguo",
            games_this_year=3,
            c_england=1,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=0,
            last_updated=datetime(2026, 3, 30, 12, 0, 0),
        )
        db_session.add(cache_entry)
        await db_session.commit()

        # Request similarity detection with partial name
        resp = await client.post("/api/snapshot/notion/fetch", json={"snapshot_names": ["Renato"]})
        assert resp.status_code == 200
        data = resp.json()
        assert "similar_names" in data
        # Should detect "Renato" as similar to "Renato Alegre"
        assert len(data["similar_names"]) > 0
        assert any(
            match["notion_name"] == "Renato Alegre" and match["snapshot"] == "Renato"
            for match in data["similar_names"]
        )


# ── POST /api/notion/force_refresh ────────────────────────────────────────────


class TestApiNotionForceRefresh:
    async def test_force_refresh_triggers_cache_update(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Force refresh should trigger an immediate cache update."""
        with (
            patch(
                "backend.api.routers.sync.notion_cache_to_db", new_callable=AsyncMock
            ) as mock_update,
            patch(
                "backend.api.routers.sync.fetch_notion_data",
                new_callable=AsyncMock,
                return_value=([], {}, MagicMock()),
            ),
        ):
            resp = await client.post("/api/notion/force_refresh")
            assert resp.status_code == 200
            mock_update.assert_called_once()

    async def test_force_refresh_returns_success(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Force refresh should return a success message."""

        with (
            patch("backend.api.routers.sync.notion_cache_to_db", new_callable=AsyncMock),
            patch(
                "backend.api.routers.sync.fetch_notion_data",
                new_callable=AsyncMock,
                return_value=([], {}, MagicMock()),
            ),
        ):
            resp = await client.post("/api/notion/force_refresh")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data or "message" in data


# ── run_notion_sync_background Tests ──────────────────────────────────────────


class TestNotionSyncBackground:
    """
    Regression tests for run_notion_sync_background.
    Prevents silent crashes from outdated imports and JSON key mismatches.
    """

    async def test_run_sync_creates_snapshot_successfully(
        self,
        background_test_engine: Any,
    ) -> None:
        """
        Regression test: run_notion_sync_background must create snapshots successfully.
        Previously crashed due to:
        - Outdated Event imports
        - Spanish/English JSON key mismatches (participaciones vs games_this_year)
        """

        from backend.sync.notion_sync import run_notion_sync_background

        # Use the shared test engine from the fixture
        test_engine = background_test_engine

        # Mock Notion data with correct structure (matching real Notion API format)
        mock_pages: list[dict[str, Any]] = [
            {
                "id": "mock_id_alice",
                "properties": {
                    "Nombre": {"title": [{"plain_text": "Alice"}]},
                    "Participaciones": {"relation": [{"id": "hist_1"}]},  # Has history
                    "Alias": {"rich_text": []},
                    "∀ 🇬🇧": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇫🇷": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇩🇪": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇮🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇦🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇷🇺": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇹🇷": {"type": "formula", "formula": {"number": 0}},
                },
            },
            {
                "id": "mock_id_bob",
                "properties": {
                    "Nombre": {"title": [{"plain_text": "Bob"}]},
                    "Participaciones": {"relation": []},  # No history
                    "Alias": {"rich_text": []},
                    "∀ 🇬🇧": {"type": "formula", "formula": {"number": 1}},
                    "∀ 🇫🇷": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇩🇪": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇮🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇦🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇷🇺": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇹🇷": {"type": "formula", "formula": {"number": 0}},
                },
            },
        ]
        mock_conteo = {
            "mock_id_alice": 5,  # Alice played 5 games this year
            "mock_id_bob": 2,  # Bob played 2 games this year
        }
        mock_client = MagicMock()

        # Patch both _fetch_notion_data and async_engine to use test engine
        with (
            patch(
                "backend.sync.notion_sync.fetch_notion_data",
                return_value=(mock_pages, mock_conteo, mock_client),
                new_callable=AsyncMock,
            ),
            patch(
                "backend.sync.notion_sync.async_engine",
                test_engine,
            ),
        ):
            # Run sync with force=True (initial snapshot, no parent)
            snapshot_id = await run_notion_sync_background(None, force=True)

        # Assert snapshot was created
        assert snapshot_id is not None
        assert isinstance(snapshot_id, int)

        # Query database using test engine to verify players were saved correctly
        from sqlalchemy.ext.asyncio import AsyncSession

        from backend.crud.snapshots import get_snapshot_players

        async with AsyncSession(test_engine) as session:
            players = await get_snapshot_players(session, snapshot_id)
            assert len(players) == 2

            # Build lookup by name
            players_by_name = {p["nombre"]: p for p in players}

            # Verify Alice data (Antiguo with 5 games)
            assert "Alice" in players_by_name
            alice = players_by_name["Alice"]
            assert alice["experiencia"] == "Antiguo"
            assert alice["juegos_este_ano"] == 5
            assert alice.get("c_england", 0) == 0
            assert alice.get("c_france", 0) == 0

            # Verify Bob data (Nuevo with 2 games)
            assert "Bob" in players_by_name
            bob = players_by_name["Bob"]
            assert bob["experiencia"] == "Nuevo"
            assert bob["juegos_este_ano"] == 2
            assert bob.get("c_england", 0) == 1  # Has England preference

    async def test_run_sync_applies_merges_and_renames(
        self,
        background_test_engine: Any,
    ) -> None:
        """
        Regression test: merges with action='merge_notion' must formally rename
        the player in the database, preserving continuity.
        Previously, the player was treated as new, breaking game history.
        """

        from sqlalchemy.ext.asyncio import AsyncSession

        from backend.crud.snapshots import get_snapshot_players
        from backend.sync.notion_sync import run_notion_sync_background

        # Use the shared test engine from the fixture
        test_engine = background_test_engine

        # Step 1: Create initial snapshot with "AliceOld" (games_this_year=0)
        from backend.crud.players import get_or_create_player
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

        async with AsyncSession(test_engine) as session:
            snap_id = await create_snapshot(session, "test_source")
            player_id = await get_or_create_player(session, "AliceOld")
            await add_player_to_snapshot(
                session, snap_id, player_id, "Nuevo", 0, 1, 0, has_priority=False
            )
            await session.commit()

        # Step 2: Mock Notion API to return "AliceNew" with games=10
        mock_pages: list[dict[str, Any]] = [
            {
                "id": "mock_id_alice_new",
                "properties": {
                    "Nombre": {"title": [{"plain_text": "AliceNew"}]},
                    "Participaciones": {"relation": [{"id": "hist_1"}]},
                    "Alias": {"rich_text": []},
                    "∀ 🇬🇧": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇫🇷": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇩🇪": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇮🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇦🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇷🇺": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇹🇷": {"type": "formula", "formula": {"number": 0}},
                },
            },
        ]
        mock_conteo = {"mock_id_alice_new": 10}  # AliceNew played 10 games this year
        mock_client = MagicMock()

        # Step 3: Run sync with merges payload renaming AliceOld -> AliceNew
        with (
            patch(
                "backend.sync.notion_sync.fetch_notion_data",
                return_value=(mock_pages, mock_conteo, mock_client),
                new_callable=AsyncMock,
            ),
            patch(
                "backend.sync.notion_sync.async_engine",
                test_engine,
            ),
        ):
            new_snap_id = await run_notion_sync_background(
                snap_id,
                force=True,
                merges={"AliceOld": {"to": "AliceNew", "action": "merge_notion"}},
            )

        # Assert snapshot was created/updated (may be same ID if in-place update)
        assert new_snap_id is not None
        assert isinstance(new_snap_id, int)

        # Step 4: Verify DB state - AliceOld renamed to AliceNew with games=10
        async with AsyncSession(test_engine) as session:
            players = await get_snapshot_players(session, new_snap_id)
            assert len(players) == 1

            player = players[0]
            # Old name should be gone, new name should exist
            assert player["nombre"] == "AliceNew"
            # Games this year should be updated from Notion (10)
            assert player["juegos_este_ano"] == 10

            # Verify the player was renamed in the players table (continuity)
            from sqlalchemy import select

            from backend.db.models import Player

            result = await session.execute(select(Player.name))
            player_names = [row[0] for row in result.fetchall()]
            assert "AliceOld" not in player_names
            assert "AliceNew" in player_names

    async def test_sync_in_place_update_logs_history(
        self,
        background_test_engine: Any,
    ) -> None:
        """
        Regression test: When syncing with Notion updates a snapshot in-place,
        the previous roster should be logged to SnapshotHistory.
        """

        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        from backend.crud.snapshots import create_snapshot
        from backend.db.models import SnapshotHistory
        from backend.sync.notion_sync import run_notion_sync_background

        # Use the shared test engine from the fixture
        test_engine = background_test_engine

        # Step 1: Create initial snapshot with 2 players
        from backend.crud.players import get_or_create_player
        from backend.crud.snapshots import add_player_to_snapshot

        async with AsyncSession(test_engine) as session:
            snap_id = await create_snapshot(session, "notion_sync")
            player1_id = await get_or_create_player(session, "Alice")
            player2_id = await get_or_create_player(session, "Bob")
            await add_player_to_snapshot(
                session, snap_id, player1_id, "Nuevo", 0, 1, 0, has_priority=False
            )
            await add_player_to_snapshot(
                session, snap_id, player2_id, "Nuevo", 0, 1, 0, has_priority=False
            )
            await session.commit()

        # Step 2: Verify no history exists yet
        async with AsyncSession(test_engine) as session:
            result = await session.execute(
                select(SnapshotHistory).where(SnapshotHistory.snapshot_id == snap_id)
            )
            assert result.scalars().first() is None

        # Step 3: Mock Notion API to return updated roster (Alice with more games, Bob removed, Charlie added)
        mock_pages: list[dict[str, Any]] = [
            {
                "id": "mock_id_alice",
                "properties": {
                    "Nombre": {"title": [{"plain_text": "Alice"}]},
                    "Participaciones": {
                        "relation": [{"id": "hist_1"}, {"id": "hist_2"}]
                    },  # More games
                    "Alias": {"rich_text": []},
                    "∀ 🇬🇧": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇫🇷": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇩🇪": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇮🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇦🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇷🇺": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇹🇷": {"type": "formula", "formula": {"number": 0}},
                },
            },
            {
                "id": "mock_id_charlie",
                "properties": {
                    "Nombre": {"title": [{"plain_text": "Charlie"}]},
                    "Participaciones": {"relation": []},
                    "Alias": {"rich_text": []},
                    "∀ 🇬🇧": {"type": "formula", "formula": {"number": 1}},
                    "∀ 🇫🇷": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇩🇪": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇮🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇦🇹": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇷🇺": {"type": "formula", "formula": {"number": 0}},
                    "∀ 🇹🇷": {"type": "formula", "formula": {"number": 0}},
                },
            },
        ]
        mock_conteo = {
            "mock_id_alice": 7,  # Alice now has 7 games
            "mock_id_charlie": 0,  # Charlie is new
        }
        mock_client = MagicMock()

        # Step 4: Run sync (should update in-place and log history)
        with (
            patch(
                "backend.sync.notion_sync.fetch_notion_data",
                return_value=(mock_pages, mock_conteo, mock_client),
                new_callable=AsyncMock,
            ),
            patch(
                "backend.sync.notion_sync.async_engine",
                test_engine,
            ),
        ):
            result_snap_id = await run_notion_sync_background(snap_id, force=True)

        # Step 5: Verify the snapshot was updated in place (same ID)
        assert result_snap_id == snap_id

        # Step 6: Verify SnapshotHistory entry was created with previous roster
        async with AsyncSession(test_engine) as session:
            result = await session.execute(
                select(SnapshotHistory)
                .where(SnapshotHistory.snapshot_id == snap_id)
                .order_by(SnapshotHistory.created_at.desc())
            )
            history_records = result.scalars().all()

            # Should have exactly one history entry from the sync
            assert len(history_records) == 1
            history = history_records[0]

            # Verify history metadata
            assert history.action_type == "notion_sync"
            # With STRICT ROSTER RULE: sync only updates existing players, never adds/removes
            # - Alice: modified (juegos_este_ano 0 -> 7, experiencia Nuevo -> Antiguo)
            # - Bob: remains (no changes)
            # - Charlie: ignored (new players not added to existing snapshots)
            assert history.changes["added"] == []
            assert history.changes["removed"] == []
            assert history.changes["renamed"] == []
            assert len(history.changes["modified"]) == 1
            assert history.changes["modified"][0]["nombre"] == "Alice"
            assert "players" in history.previous_state

            # Verify the previous roster is stored (Alice, Bob)
            previous_players: list[dict[str, object]] = history.previous_state["players"]  # type: ignore[assignment]
            assert len(previous_players) == 2
            previous_names = {p["nombre"] for p in previous_players}
            assert previous_names == {"Alice", "Bob"}
