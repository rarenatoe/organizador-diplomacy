"""
test_views.py — Regression tests for view queries.

Tests to prevent tuple indexing errors in SQL result processing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from backend.db.crud import (
    add_mesa_player,
    create_game_event,
    create_mesa,
    create_snapshot,
    get_or_create_player,
)
from backend.db.models import NotionCache
from backend.db.views import get_game_event_detail

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
        from backend.db.crud import add_player_to_snapshot

        await add_player_to_snapshot(db_session, snap1, pid1, "Antiguo", 5, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap1, pid2, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()

        # Insert NotionCache with different c_turkey values
        nc1 = NotionCache(
            notion_id="test1",
            nombre="PlayerWithHighTurkey",
            experiencia="Antiguo",
            juegos_este_ano=5,
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
            nombre="PlayerWithZeroTurkey",
            experiencia="Antiguo",
            juegos_este_ano=0,
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

        # Create game event with mesas
        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        await db_session.commit()

        mesa_id = await create_mesa(db_session, event_id, 1)
        await db_session.commit()

        # Assign players to mesa with specific countries (NOT Turkey)
        await add_mesa_player(db_session, mesa_id, pid1, 1, "England")
        await add_mesa_player(db_session, mesa_id, pid2, 2, "France")
        await db_session.commit()

        # Test: Get game detail
        detail = await get_game_event_detail(db_session, event_id)
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
            from backend.db.crud import add_player_to_snapshot

            await add_player_to_snapshot(db_session, snap1, pid, "Antiguo", i, 1, 2, 0)
        await db_session.commit()

        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        await db_session.commit()

        mesa_id = await create_mesa(db_session, event_id, 1)
        await db_session.commit()

        # Add all players to mesa with their respective countries
        for i, (pid, country) in enumerate(zip(player_ids, countries, strict=True)):
            await add_mesa_player(db_session, mesa_id, pid, i + 1, country)
        await db_session.commit()

        # Test
        detail = await get_game_event_detail(db_session, event_id)
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

        from backend.db.crud import add_player_to_snapshot

        await add_player_to_snapshot(db_session, snap1, pid, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()

        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        await db_session.commit()

        mesa_id = await create_mesa(db_session, event_id, 1)
        await db_session.commit()

        # Add player with empty string pais (NOT NULL constraint requires a value)
        await add_mesa_player(db_session, mesa_id, pid, 1, "")
        await db_session.commit()

        # Test
        detail = await get_game_event_detail(db_session, event_id)
        assert detail is not None

        # Verify: Empty pais should result in empty string
        player = detail["mesas"][0]["jugadores"][0]
        assert player["pais"] == "", f"Empty pais should return empty string, got: {player['pais']}"


class TestPaisReasonPersistence:
    """
    Regression tests for pais_reason field persistence.

    Previously, pais_reason was generated by the algorithm but not saved to the database.
    This test verifies the full persistence flow:
    1. save_game_draft_async receives pais_reason in the draft payload
    2. add_mesa_player stores it in mesa_players.pais_reason
    3. get_game_event_detail retrieves it correctly
    """

    async def test_pais_reason_persists_and_retrieves(self, db_session: Any) -> None:
        """
        Verify pais_reason is persisted to the database and retrieved correctly.

        This is a regression test for the pais_reason field that was previously
        generated but not saved. The field is used to explain why a country
        was assigned to a player (e.g., shielding algorithm decisions).
        """
        # Setup: Create game with players having pais_reason
        snap1 = await create_snapshot(db_session, "manual")

        # Create two players with different pais_reason values
        pid1 = await get_or_create_player(db_session, "PlayerWithReason")
        pid2 = await get_or_create_player(db_session, "PlayerWithoutReason")

        await db_session.commit()

        # Add players to snapshot
        from backend.db.crud import add_player_to_snapshot

        await add_player_to_snapshot(db_session, snap1, pid1, "Antiguo", 5, 1, 2, 0)
        await add_player_to_snapshot(db_session, snap1, pid2, "Antiguo", 3, 1, 2, 0)
        await db_session.commit()

        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        await db_session.commit()

        mesa_id = await create_mesa(db_session, event_id, 1)
        await db_session.commit()

        # Key test: Add players with pais_reason
        reason_text = "Cualquier jugador disponible podía recibir este país; se asignó para evitar que Alice lo repita (3 veces)."
        await add_mesa_player(db_session, mesa_id, pid1, 1, "England", pais_reason=reason_text)
        await add_mesa_player(
            db_session,
            mesa_id,
            pid2,
            2,
            "France",
            pais_reason=None,  # No reason
        )
        await db_session.commit()

        # Test: Retrieve game detail
        detail = await get_game_event_detail(db_session, event_id)
        assert detail is not None

        # Verify: pais_reason is correctly returned
        assert len(detail["mesas"]) == 1
        jugadores = detail["mesas"][0]["jugadores"]
        assert len(jugadores) == 2

        # Find players by name
        player_data = {j["nombre"]: j for j in jugadores}

        # Player with pais_reason should have it in the response
        assert "PlayerWithReason" in player_data
        assert player_data["PlayerWithReason"]["pais_reason"] == reason_text, (
            f"Expected pais_reason to be persisted and retrieved. "
            f"Got: {player_data['PlayerWithReason'].get('pais_reason')}"
        )

        # Player without pais_reason should have None or empty
        assert "PlayerWithoutReason" in player_data
        assert player_data["PlayerWithoutReason"]["pais_reason"] in (
            None,
            "",
        ), (
            f"Expected no pais_reason for player 2, got: {player_data['PlayerWithoutReason'].get('pais_reason')}"
        )

    async def test_multiple_players_same_pais_reason(self, db_session: Any) -> None:
        """
        Verify multiple players can have the same pais_reason.

        This is common when the shielding algorithm assigns countries
        for the same reason (e.g., multiple players shielding one cursed player).
        """
        snap1 = await create_snapshot(db_session, "manual")
        snap2 = await create_snapshot(db_session, "organizar")
        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        mesa_id = await create_mesa(db_session, event_id, 1)

        # Create 3 players with the same reason
        shared_reason = "Assigned to shield cursed player Bob from repeating Turkey."
        pids: list[int] = []
        for i in range(3):
            pid = await get_or_create_player(db_session, f"Player{i}")
            pids.append(pid)

        await db_session.commit()

        # Add all players with same reason
        for i, pid in enumerate(pids):
            await add_mesa_player(
                db_session, mesa_id, pid, i + 1, "England", pais_reason=shared_reason
            )
        await db_session.commit()

        # Retrieve and verify
        detail = await get_game_event_detail(db_session, event_id)
        assert detail is not None  # Ensure detail is not None
        jugadores = detail["mesas"][0]["jugadores"]

        for jugador in jugadores:
            assert jugador["pais_reason"] == shared_reason, (
                f"Expected all players to have same reason, got: {jugador.get('pais_reason')}"
            )

    async def test_pais_reason_with_special_characters(self, db_session: Any) -> None:
        """
        Verify pais_reason correctly handles special characters and accents.

        Spanish text often contains accents and special characters that should be
        preserved through the persistence layer.
        """
        snap1 = await create_snapshot(db_session, "manual")
        pid = await get_or_create_player(db_session, "PlayerWithAccents")

        # Add player to snapshot
        from backend.db.crud import add_player_to_snapshot

        await add_player_to_snapshot(db_session, snap1, pid, "Antiguo", 0, 1, 2, 0)
        await db_session.commit()

        # Insert NotionCache for the player
        nc = NotionCache(
            notion_id="test_accents",
            nombre="PlayerWithAccents",
            experiencia="Antiguo",
            juegos_este_ano=0,
            c_england=0,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=0,
            last_updated=datetime.now(),
        )
        db_session.add(nc)
        await db_session.commit()

        snap2 = await create_snapshot(db_session, "organizar")
        await db_session.commit()

        event_id = await create_game_event(db_session, snap1, snap2, 1, "copypaste")
        await db_session.commit()

        mesa_id = await create_mesa(db_session, event_id, 1)
        await db_session.commit()

        # Use special characters: accents, ñ, quotes, parentheses
        reason_with_accents = (
            "Asignación especial: país necesitaba protección de repetición (3 veces)."
        )

        await add_mesa_player(
            db_session, mesa_id, pid, 1, "Germany", pais_reason=reason_with_accents
        )
        await db_session.commit()

        # Retrieve and verify
        detail = await get_game_event_detail(db_session, event_id)
        assert detail is not None  # Ensure detail is not None
        player = detail["mesas"][0]["jugadores"][0]

        assert player["pais_reason"] == reason_with_accents, (
            f"Special characters should be preserved. "
            f"Expected: {reason_with_accents}, got: {player.get('pais_reason')}"
        )
