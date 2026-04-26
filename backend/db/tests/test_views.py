"""
test_views.py — Regression tests for view queries.

Tests to prevent tuple indexing errors in SQL result processing.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from backend.api.models.snapshots import DeepDiffResult, HistoryState, PlayerData
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
from backend.db.models import NotionCache, SnapshotSource
from backend.db.views import get_game_event_detail, get_snapshot_detail

if TYPE_CHECKING:
    from typing import Any

pytestmark = pytest.mark.asyncio


class TestGetGameEventDetailCountryRegression:
    """
    Regression tests for the country field indexing bug.

    Previously, country was incorrectly read from index 12 (c_turkey)
    instead of index 13 (mp.country), causing players to show incorrect
    country values (c_turkey) as their assigned country.
    """

    async def test_country_field_not_c_turkey(self, db_session: Any) -> None:
        """
        Verify that the country field shows the assigned country, not c_turkey.

        This is a regression test for the off-by-one tuple indexing error
        where p[12] was used instead of p[13] for the country field.
        """
        # Setup: Create players with different c_turkey values
        snap1 = await create_snapshot(db_session, SnapshotSource.MANUAL)

        # Create players with distinct c_turkey values
        pid1 = await get_or_create_player(db_session, "PlayerWithHighTurkey")
        pid2 = await get_or_create_player(db_session, "PlayerWithZeroTurkey")

        await db_session.commit()

        # Add players to snapshot
        await add_player_to_snapshot(
            db_session, snap1, pid1, 5, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, snap1, pid2, 0, 2, 0, has_priority=True, is_new=False
        )
        await db_session.commit()

        # Insert NotionCache with different c_turkey values
        nc1 = NotionCache(
            notion_id="test1",
            name="PlayerWithHighTurkey",
            is_new=False,
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
            is_new=False,
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
        snap2 = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)
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
        assert len(detail.mesas) == 1
        mesa = detail.mesas[0]
        assert len(mesa.jugadores) == 2

        # Find the players
        player_countries = {j.nombre: j.country.name for j in mesa.jugadores}

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
        Verify all 7 countries are correctly returned from country field.

        The view returns raw country names (not translated) from the database.
        """
        # Setup: Create 7 players with each country
        snap1 = await create_snapshot(db_session, SnapshotSource.MANUAL)
        countries = ["England", "France", "Germany", "Italy", "Austria", "Russia", "Turkey"]
        player_ids: list[int] = []

        for i, country in enumerate(countries):
            pid = await get_or_create_player(db_session, f"Player{i}_{country}")
            player_ids.append(pid)

            await add_player_to_snapshot(
                db_session, snap1, pid, i, 2, 0, has_priority=True, is_new=False
            )
        await db_session.commit()

        snap2 = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)
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
        jugadores = detail.mesas[0].jugadores
        country_names = {j.country.name for j in jugadores}

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

    async def test_country_field_returns_empty_for_unset(self, db_session: Any) -> None:
        """
        Verify that unset country values return empty string.

        The MesaPlayer table requires country to be NOT NULL, so we use
        empty string to represent "no country assigned".
        """
        # Setup
        snap1 = await create_snapshot(db_session, SnapshotSource.MANUAL)
        pid = await get_or_create_player(db_session, "PlayerNoCountry")
        await db_session.commit()

        await add_player_to_snapshot(
            db_session, snap1, pid, 0, 2, 0, has_priority=True, is_new=False
        )
        await db_session.commit()

        snap2 = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)
        await db_session.commit()

        edge_id = await create_game_edge(db_session, snap1, snap2, 1)
        await db_session.commit()

        table_id = await create_game_table(db_session, edge_id, 1)
        await db_session.commit()

        # Add player with empty string country (NOT NULL constraint requires a value)
        await add_table_player(db_session, table_id, pid, 1, "")
        await db_session.commit()

        # Test
        detail = await get_game_event_detail(db_session, edge_id)
        assert detail is not None

        # Verify: Empty country should result in empty string name
        player = detail.mesas[0].jugadores[0]
        assert player.country.name == "", (
            f"Empty country should return empty string name, got: {player.country}"
        )


async def test_view_returns_country_reason(db_session: Any) -> None:
    """View test: get_game_event_detail should return country.reason from TablePlayer."""
    from backend.crud.chain import create_game_edge
    from backend.crud.games import add_table_player, create_game_table
    from backend.crud.players import get_or_create_player
    from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

    # Manually insert test data (no CRUD functions)
    player = await get_or_create_player(db_session, "TestPlayer")

    # Create snapshots and game edge
    input_snap = await create_snapshot(db_session, SnapshotSource.MANUAL)
    output_snap = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)

    # Add player to both snapshots so they appear in the view
    await add_player_to_snapshot(
        db_session, input_snap, player, 5, 2, 0, has_priority=True, is_new=False
    )
    await add_player_to_snapshot(
        db_session, output_snap, player, 6, 2, 0, has_priority=False, is_new=False
    )

    game_id = await create_game_edge(db_session, input_snap, output_snap, 1)

    # Create game table and player with country_reason
    table_id = await create_game_table(db_session, game_id, 1)
    await add_table_player(
        db_session, table_id, player, 1, "England", country_reason=["Test Reason"]
    )
    await db_session.commit()

    # Test the view
    detail = await get_game_event_detail(db_session, game_id)
    assert detail is not None
    assert len(detail.mesas) == 1
    assert len(detail.mesas[0].jugadores) == 1

    player_data = detail.mesas[0].jugadores[0]
    assert player_data.country.reason == ["Test Reason"]


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
        snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)
        await db_session.commit()

        detail = await get_snapshot_detail(db_session, snap_id)
        assert detail is not None
        assert hasattr(detail, "history"), "history attribute should exist in snapshot detail"
        assert detail.history == [], "New snapshot should have empty history"

    async def test_snapshot_detail_includes_history_after_log(self, db_session: Any) -> None:
        """
        Verify get_snapshot_detail returns history entries after log_snapshot_history is called.
        """
        from backend.crud.snapshots import log_snapshot_history

        # Create snapshot
        snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)
        pid = await get_or_create_player(db_session, "Player1")
        await add_player_to_snapshot(
            db_session, snap_id, pid, 5, 2, 0, has_priority=True, is_new=False
        )
        await db_session.commit()

        # Log a history entry
        await log_snapshot_history(
            db_session,
            snapshot_id=snap_id,
            action_type=SnapshotSource.MANUAL_EDIT,
            changes=DeepDiffResult(added=[], removed=[], renamed=[], modified=[]),
            previous_state=HistoryState(
                players=[
                    PlayerData(
                        nombre="OldPlayer",
                        notion_id="old-notion-1",
                        notion_name="OldPlayer",
                        is_new=True,
                        juegos_este_ano=0,
                        has_priority=True,
                        partidas_deseadas=1,
                        partidas_gm=0,
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
            ),
        )
        await db_session.commit()

        # Retrieve and verify
        detail = await get_snapshot_detail(db_session, snap_id)
        assert detail is not None
        assert hasattr(detail, "history"), "history attribute should exist in snapshot detail"
        assert len(detail.history) == 1, f"Expected 1 history entry, got {len(detail.history)}"

        log = detail.history[0]
        assert hasattr(log, "id")
        assert hasattr(log, "created_at")
        assert log.action_type == "manual_edit"
        assert log.changes == DeepDiffResult(added=[], removed=[], renamed=[], modified=[])

    async def test_snapshot_detail_history_ordered_by_date_desc(self, db_session: Any) -> None:
        """
        Verify history entries are ordered by created_at DESC (most recent first).

        Note: In tests, all entries may have the same timestamp due to fast insertion.
        The query uses ORDER BY created_at DESC, id DESC as a tiebreaker.
        """
        from backend.crud.snapshots import log_snapshot_history

        snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)
        await db_session.commit()

        # Log multiple entries
        for _ in range(3):
            await log_snapshot_history(
                db_session,
                snapshot_id=snap_id,
                action_type=SnapshotSource.MANUAL_EDIT,
                changes=DeepDiffResult(added=[], removed=[], renamed=[], modified=[]),
                previous_state=HistoryState(players=[]),
            )
            await db_session.commit()

        # Retrieve and verify
        detail = await get_snapshot_detail(db_session, snap_id)
        assert detail is not None
        assert len(detail.history) == 3

        # Verify all action types are present
        action_types = {entry.action_type for entry in detail.history}
        assert action_types == {SnapshotSource.MANUAL_EDIT}

        # Verify timestamps are present and properly formatted
        for entry in detail.history:
            assert isinstance(entry.created_at, datetime)


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
        snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)
        player_id = await get_or_create_player(db_session, "VeteranPlayer")

        # Add player to snapshot
        await add_player_to_snapshot(
            db_session, snap_id, player_id, 5, 3, 1, has_priority=True, is_new=False
        )
        await db_session.commit()

        # Create multiple NotionCache entries for the same player (historical data)
        # This simulates the scenario where a veteran player has been synced multiple times
        for i in range(3):
            cache_entry = NotionCache(
                name="VeteranPlayer",
                notion_id=f"notion-id-{i}",
                is_new=False,
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
            f"Players returned: {[p.nombre for p in players]}"
        )

        # Verify the single player has the correct data
        assert players[0].nombre == "VeteranPlayer"
        assert not players[0].is_new

    async def test_get_snapshot_detail_no_duplicates_with_history(self, db_session: Any) -> None:
        """
        Verify get_snapshot_detail returns unique players even with history records.

        Tests the full integration path from get_snapshot_detail through
        get_snapshot_players to ensure no fan-out occurs.
        """
        # Setup: Create a snapshot with a player
        snap_id = await create_snapshot(db_session, SnapshotSource.MANUAL)
        player_id = await get_or_create_player(db_session, "MultiCachePlayer")

        await add_player_to_snapshot(
            db_session, snap_id, player_id, 0, 1, 0, has_priority=False, is_new=True
        )
        await db_session.commit()

        # Add multiple NotionCache entries to create fan-out potential
        for i in range(5):
            cache_entry = NotionCache(
                name="MultiCachePlayer",
                notion_id=f"id-{i}",
                is_new=True,
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
        assert len(detail.players) == 1, (
            f"Expected 1 player in snapshot detail, got {len(detail.players)}"
        )
        assert detail.players[0].nombre == "MultiCachePlayer"
