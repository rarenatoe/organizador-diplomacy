"""
test_views.py — Regression tests for view queries.

Tests to prevent tuple indexing errors in SQL result processing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from backend.crud.chain import create_game_edge
from backend.crud.games import (
    add_table_player,
    create_game_table,
)
from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
)
from backend.db.models import NotionCache
from backend.db.views import get_game_event_detail, get_snapshot_detail

pytestmark = pytest.mark.asyncio


class TestGetGameEventDetailPaisRegression:
    """
    Regression tests for the pais field indexing bug.

    Previously, pais was incorrectly read from index 12 (c_turkey)
    instead of index 13 (mp.pais), causing players to show incorrect
    country values (c_turkey) as their assigned country.
    """

    async def test_pais_field_not_c_turkey(self, db_session: Any) -> None:
        """
        Verify that the pais field shows the assigned country, not c_turkey.

        This is a regression test for the off-by-one tuple indexing error
        where p[12] was used instead of p[13] for the pais field.
        """
        # Setup: Create players with different c_turkey values
        snap1 = await create_snapshot(db_session, "manual")

        # Create players with distinct c_turkey values
        pid1 = await get_or_create_player(db_session, "PlayerWithHighTurkey")
        pid2 = await get_or_create_player(db_session, "PlayerWithZeroTurkey")

        await db_session.commit()

        # Add players to snapshot
        await add_player_to_snapshot(db_session, snap1, pid1, "Antiguo", 5, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap1, pid2, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()

        # Insert NotionCache with different c_turkey values
        nc1 = NotionCache(
            notion_id="test1",
            name="PlayerWithHighTurkey",
            experience="Antiguo",
            games_this_year=5,
            c_england=0,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=99,  # High value - would show as 99 if p[12] was used
            last_updated=datetime.now(),  # Use datetime object
        )
        nc2 = NotionCache(
            notion_id="test2",
            name="PlayerWithZeroTurkey",
            experience="Antiguo",
            games_this_year=0,
            c_england=0,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=0,  # Zero value - would show as empty if p[12] was used
            last_updated=datetime.now(),  # Use datetime object
        )
        db_session.add_all([nc1, nc2])
        await db_session.commit()

        # Create game event with tables
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        edge_id = await create_game_edge(db_session, snap1, snap2, 1)
        await db_session.commit()

        table_id = await create_game_table(db_session, edge_id, 1)
        await db_session.commit()

        # Assign players to table with specific countries (NOT Turkey)
        await add_table_player(db_session, table_id, pid1, 1, "England")
        await add_table_player(db_session, table_id, pid2, 2, "France")
        await db_session.commit()

        # Test: Get game detail
        detail = await get_game_event_detail(db_session, edge_id)
        assert detail is not None

        # Verify: Players should show their assigned countries, not c_turkey
        assert len(detail["mesas"]) == 1
        mesa = detail["mesas"][0]
        assert len(mesa["jugadores"]) == 2

        # Find the players
        player_countries = {j["nombre"]: j["pais"] for j in mesa["jugadores"]}

        # Key assertion: PlayerWithHighTurkey should show "England", not 99 (c_turkey)
        # If the bug existed (p[12] instead of p[13]), this would show c_turkey value (99)
        assert player_countries.get("PlayerWithHighTurkey") == "England", (
            "Player with high c_turkey should show assigned country (England), "
            f"not c_turkey value. Got: {player_countries.get('PlayerWithHighTurkey')}"
        )

        # PlayerWithZeroTurkey should show "France", not empty/zero from c_turkey=0
        assert player_countries.get("PlayerWithZeroTurkey") == "France", (
            "Player with zero c_turkey should show assigned country (France), "
            f"not empty. Got: {player_countries.get('PlayerWithZeroTurkey')}"
        )

    async def test_all_countries_correctly_returned(self, db_session: Any) -> None:
        """
        Verify all 7 countries are correctly returned from pais field.

        The view returns raw country names (not translated) from the database.
        """
        # Setup: Create 7 players with each country
        snap1 = await create_snapshot(db_session, "manual")
        countries = ["England", "France", "Germany", "Italy", "Austria", "Russia", "Turkey"]
        player_ids: list[int] = []

        for i, country in enumerate(countries):
            pid = await get_or_create_player(db_session, f"Player{i}_{country}")
            player_ids.append(pid)

            await add_player_to_snapshot(db_session, snap1, pid, "Antiguo", i, 1, 2, 0)
        await db_session.commit()

        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        edge_id = await create_game_edge(db_session, snap1, snap2, 1)
        await db_session.commit()

        table_id = await create_game_table(db_session, edge_id, 1)
        await db_session.commit()

        # Add all players to table with their respective countries
        for i, (pid, country) in enumerate(zip(player_ids, countries, strict=True)):
            await add_table_player(db_session, table_id, pid, i + 1, country)
        await db_session.commit()

        # Test
        detail = await get_game_event_detail(db_session, edge_id)
        assert detail is not None

        # Verify all countries are correctly returned (raw values, not translated)
        jugadores = detail["mesas"][0]["jugadores"]
        country_names = {j["pais"] for j in jugadores}

        expected_countries = {
            "England",
            "France",
            "Germany",
            "Italy",
            "Austria",
            "Russia",
            "Turkey",
        }

        assert country_names == expected_countries, (
            f"Expected all 7 countries, got: {country_names}"
        )

    async def test_pais_field_returns_empty_for_unset(self, db_session: Any) -> None:
        """
        Verify that unset pais values return empty string.

        The MesaPlayer table requires pais to be NOT NULL, so we use
        empty string to represent "no country assigned".
        """
        # Setup
        snap1 = await create_snapshot(db_session, "manual")
        pid = await get_or_create_player(db_session, "PlayerNoCountry")
        await db_session.commit()

        await add_player_to_snapshot(db_session, snap1, pid, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()

        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        edge_id = await create_game_edge(db_session, snap1, snap2, 1)
        await db_session.commit()

        table_id = await create_game_table(db_session, edge_id, 1)
        await db_session.commit()

        # Add player with empty string pais (NOT NULL constraint requires a value)
        await add_table_player(db_session, table_id, pid, 1, "")
        await db_session.commit()

        # Test
        detail = await get_game_event_detail(db_session, edge_id)
        assert detail is not None

        # Verify: Empty pais should result in empty string
        player = detail["mesas"][0]["jugadores"][0]
        assert player["pais"] == "", f"Empty pais should return empty string, got: {player['pais']}"


async def test_view_returns_pais_reason(db_session: Any) -> None:
    """View test: get_game_event_detail should return pais_reason from TablePlayer."""
    from backend.crud.chain import create_game_edge
    from backend.crud.games import add_table_player, create_game_table
    from backend.crud.players import get_or_create_player
    from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

    # Manually insert test data (no CRUD functions)
    player = await get_or_create_player(db_session, "TestPlayer")

    # Create snapshots and game edge
    input_snap = await create_snapshot(db_session, "manual")
    output_snap = await create_snapshot(db_session, "organizar")

    # Add player to both snapshots so they appear in the view
    await add_player_to_snapshot(db_session, input_snap, player, "Antiguo", 5, 1, 2, 0)
    await add_player_to_snapshot(db_session, output_snap, player, "Antiguo", 6, 0, 2, 0)

    game_id = await create_game_edge(db_session, input_snap, output_snap, 1)

    # Create game table and player with country_reason
    table_id = await create_game_table(db_session, game_id, 1)
    await add_table_player(db_session, table_id, player, 1, "England", country_reason="Test Reason")
    await db_session.commit()

    # Test the view
    detail = await get_game_event_detail(db_session, game_id)
    assert detail is not None
    assert len(detail["mesas"]) == 1
    assert len(detail["mesas"][0]["jugadores"]) == 1

    player_data = detail["mesas"][0]["jugadores"][0]
    assert player_data["pais_reason"] == "Test Reason"


class TestSnapshotHistoryInDetail:
    """
    Regression tests for snapshot history feature.

    The history feature was fully implemented (log creation triggers in sync/save)
    but was not being returned by the API. This test verifies the fix.
    """

    async def test_snapshot_detail_includes_empty_history(self, db_session: Any) -> None:
        """
        Verify get_snapshot_detail returns an empty history array for new snapshots.
        """
        snap_id = await create_snapshot(db_session, "manual")
        await db_session.commit()

        detail = await get_snapshot_detail(db_session, snap_id)
        assert detail is not None
        assert "history" in detail, "history key should exist in snapshot detail"
        assert detail["history"] == [], "New snapshot should have empty history"

    async def test_snapshot_detail_includes_history_after_log(self, db_session: Any) -> None:
        """
        Verify get_snapshot_detail returns history entries after log_snapshot_history is called.
        """
        from backend.crud.snapshots import log_snapshot_history

        # Create snapshot
        snap_id = await create_snapshot(db_session, "manual")
        pid = await get_or_create_player(db_session, "Player1")
        await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", 5, 1, 2, 0)
        await db_session.commit()

        # Log a history entry
        await log_snapshot_history(
            db_session,
            snapshot_id=snap_id,
            action_type="manual_edit",
            changes={"added": [], "removed": [], "renamed": [], "modified": []},
            previous_state={"players": [{"nombre": "OldPlayer", "experiencia": "Nuevo"}]},
        )
        await db_session.commit()

        # Retrieve and verify
        detail = await get_snapshot_detail(db_session, snap_id)
        assert detail is not None
        assert "history" in detail
        assert len(detail["history"]) == 1, (
            f"Expected 1 history entry, got {len(detail['history'])}"
        )

        log = detail["history"][0]
        assert "id" in log
        assert "created_at" in log
        assert log["action_type"] == "manual_edit"
        assert log["changes"] == {"added": [], "removed": [], "renamed": [], "modified": []}

    async def test_snapshot_detail_history_ordered_by_date_desc(self, db_session: Any) -> None:
        """
        Verify history entries are ordered by created_at DESC (most recent first).

        Note: In tests, all entries may have the same timestamp due to fast insertion.
        The query uses ORDER BY created_at DESC, id DESC as a tiebreaker.
        """
        from backend.crud.snapshots import log_snapshot_history

        snap_id = await create_snapshot(db_session, "manual")
        await db_session.commit()

        # Log multiple entries
        for i in range(3):
            await log_snapshot_history(
                db_session,
                snapshot_id=snap_id,
                action_type=f"action_{i}",
                changes={"added": [], "removed": [], "renamed": [], "modified": []},
                previous_state={"players": []},
            )
            await db_session.commit()

        # Retrieve and verify
        detail = await get_snapshot_detail(db_session, snap_id)
        assert detail is not None
        assert len(detail["history"]) == 3

        # Verify all action types are present
        action_types = {entry["action_type"] for entry in detail["history"]}
        assert action_types == {"action_0", "action_1", "action_2"}

        # Verify timestamps are present and properly formatted
        for entry in detail["history"]:
            assert "created_at" in entry
            assert isinstance(entry["created_at"], str)


class TestGetSnapshotDetailFanOutRegression:
    """
    Regression tests for the JOIN fan-out bug causing duplicate players.

    When a player has multiple entries in related tables (e.g., multiple
    NotionCache entries from historical syncs), the JOIN in get_snapshot_players
    was multiplying rows, causing the same player to appear multiple times.
    """

    async def test_no_duplicate_players_with_multiple_notion_cache_entries(
        self, db_session: Any
    ) -> None:
        """
        Verify that players with multiple NotionCache entries don't appear duplicated.

        This is a regression test for the SQL JOIN fan-out bug where veteran
        players with historical records were being returned multiple times.
        """
        from backend.crud.snapshots import get_snapshot_players

        # Setup: Create a snapshot with one player
        snap_id = await create_snapshot(db_session, "manual")
        player_id = await get_or_create_player(db_session, "VeteranPlayer")

        # Add player to snapshot
        await add_player_to_snapshot(db_session, snap_id, player_id, "Antiguo", 5, 10, 3, 1)
        await db_session.commit()

        # Create multiple NotionCache entries for the same player (historical data)
        # This simulates the scenario where a veteran player has been synced multiple times
        for i in range(3):
            cache_entry = NotionCache(
                name="VeteranPlayer",
                notion_id=f"notion-id-{i}",
                experience="Antiguo",
                last_updated=datetime.now(),
                c_england=i,
                c_france=i + 1,
                c_germany=i + 2,
                c_italy=i + 3,
                c_austria=i + 4,
                c_russia=i + 5,
                c_turkey=i + 6,
            )
            db_session.add(cache_entry)
        await db_session.commit()

        # Retrieve players - should return exactly 1 player, not 3
        players = await get_snapshot_players(db_session, snap_id)

        # The bug would cause 3 rows (one per NotionCache entry) before .distinct()
        assert len(players) == 1, (
            f"Expected 1 player, got {len(players)} - JOIN fan-out bug! "
            f"Players returned: {[p['nombre'] for p in players]}"
        )

        # Verify the single player has the correct data
        assert players[0]["nombre"] == "VeteranPlayer"
        assert players[0]["experiencia"] == "Antiguo"

    async def test_get_snapshot_detail_no_duplicates_with_history(self, db_session: Any) -> None:
        """
        Verify get_snapshot_detail returns unique players even with history records.

        Tests the full integration path from get_snapshot_detail through
        get_snapshot_players to ensure no fan-out occurs.
        """
        # Setup: Create a snapshot with a player
        snap_id = await create_snapshot(db_session, "manual")
        player_id = await get_or_create_player(db_session, "MultiCachePlayer")

        await add_player_to_snapshot(db_session, snap_id, player_id, "Nuevo", 0, 0, 1, 0)
        await db_session.commit()

        # Add multiple NotionCache entries to create fan-out potential
        for i in range(5):
            cache_entry = NotionCache(
                name="MultiCachePlayer",
                notion_id=f"id-{i}",
                experience="Nuevo",
                last_updated=datetime.now(),
                c_england=1,
                c_france=2,
                c_germany=3,
                c_italy=4,
                c_austria=5,
                c_russia=6,
                c_turkey=7,
            )
            db_session.add(cache_entry)
        await db_session.commit()

        # Get full snapshot detail
        detail = await get_snapshot_detail(db_session, snap_id)

        assert detail is not None
        assert len(detail["players"]) == 1, (
            f"Expected 1 player in snapshot detail, got {len(detail['players'])}"
        )
        assert detail["players"][0]["nombre"] == "MultiCachePlayer"


class TestGetGameEventDetailNotionCacheDeduplication:
    """
    Regression tests for JOIN fan-out bug in get_game_event_detail.

    When a player has multiple NotionCache entries (historical sync data),
    the JOIN in get_game_event_detail was multiplying rows, causing the same
    player to appear multiple times in mesas[jugadores].
    """

    async def test_no_duplicate_players_with_multiple_notion_cache_entries(
        self, db_session: Any
    ) -> None:
        """
        Verify that players with multiple NotionCache entries don't appear duplicated in game event detail.

        This is a regression test for SQL JOIN fan-out bug where veteran
        players with historical records were being returned multiple times
        in the jugadores list.
        """
        # Setup: Create a snapshot with one player
        snap1 = await create_snapshot(db_session, "manual")
        player_id = await get_or_create_player(db_session, "TestPlayer")

        # Add player to snapshot
        await add_player_to_snapshot(db_session, snap1, player_id, "Antiguo", 5, 10, 3, 1)
        await db_session.commit()

        # Create game event
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        edge_id = await create_game_edge(db_session, snap1, snap2, 1)
        await db_session.commit()

        table_id = await create_game_table(db_session, edge_id, 1)
        await db_session.commit()

        # Add player to table
        await add_table_player(db_session, table_id, player_id, 1, "England")
        await db_session.commit()

        # Create 3 NotionCache entries for the same player (simulating historical sync data)
        # This would cause the JOIN fan-out bug if not properly deduplicated
        for i in range(3):
            cache_entry = NotionCache(
                name="TestPlayer",
                notion_id=f"notion-id-{i}",
                experience="Antiguo",
                last_updated=datetime.now(),
                games_this_year=5 + i,  # Different values to test max() aggregation
                c_england=i,
                c_france=i + 1,
                c_germany=i + 2,
                c_italy=i + 3,
                c_austria=i + 4,
                c_russia=i + 5,
                c_turkey=i + 6,
            )
            db_session.add(cache_entry)
        await db_session.commit()

        # Test: Call get_game_event_detail
        detail = await get_game_event_detail(db_session, edge_id)
        assert detail is not None

        # Assert: Player should appear exactly once in jugadores list
        assert len(detail["mesas"]) == 1, "Expected exactly 1 mesa"
        mesa = detail["mesas"][0]

        # The bug would cause 3 players (one per NotionCache entry)
        assert len(mesa["jugadores"]) == 1, (
            f"Expected 1 player in jugadores list, got {len(mesa['jugadores'])} - "
            "JOIN fan-out bug detected!"
        )

        # Verify the single player has correct data
        player = mesa["jugadores"][0]
        assert player["nombre"] == "TestPlayer", "Player name should match"
        assert player["pais"] == "England", "Player should show assigned country"

        # Verify max() aggregation worked correctly (should be highest values from the 3 entries)
        assert player["c_england"] == 2, "Should use max() for c_england"
        assert player["c_france"] == 3, "Should use max() for c_france"
        assert player["c_germany"] == 4, "Should use max() for c_germany"
        assert player["c_italy"] == 5, "Should use max() for c_italy"
        assert player["c_austria"] == 6, "Should use max() for c_austria"
        assert player["c_russia"] == 7, "Should use max() for c_russia"
        assert player["c_turkey"] == 8, "Should use max() for c_turkey"
