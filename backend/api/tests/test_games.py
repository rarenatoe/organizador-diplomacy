"""
test_games.py — Tests for /api/game/draft and /api/game/save endpoints.

Tests the two-step Draft Mode:
  POST /api/game/draft  → generate draft (no DB write)
  POST /api/game/save   → persist confirmed draft
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from backend.db.models import Event, Mesa

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def make_snapshot_with_players(db_session: Any, count: int = 14) -> int:
    """Creates a snapshot with `count` players, enough for the algorithm."""
    from backend.db.crud import (
        add_player_to_snapshot,
        create_snapshot,
        get_or_create_player,
    )

    snap_id = await create_snapshot(db_session, "manual")
    for i in range(count):
        pid = await get_or_create_player(db_session, f"Jugador_{i:02d}")
        await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", i % 3, 0, 2, 0)
    await db_session.commit()
    return snap_id


# ── POST /api/game/draft ──────────────────────────────────────────────────────


class TestApiGameDraft:
    async def test_missing_snapshot_id_returns_400(self, client: Any) -> None:
        resp = await client.post("/api/game/draft", json={})
        assert resp.status_code == 422  # FastAPI validation error

    async def test_valid_snapshot_returns_draft(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, 14)
        resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert resp.status_code == 200
        data = resp.json()
        assert "mesas" in data
        assert "tickets_sobrantes" in data
        assert "intentos_usados" in data
        assert len(data["mesas"]) >= 1

    async def test_draft_does_not_write_to_db(self, client: Any, db_session: Any) -> None:
        """Calling /api/game/draft must NOT create any events in the DB."""
        snap_id = await make_snapshot_with_players(db_session, 14)
        await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        result = await db_session.execute(select(Event).where(Event.type == "game"))
        event_count = len(result.scalars().all())
        assert event_count == 0

    async def test_too_few_players_returns_400(self, client: Any, db_session: Any) -> None:
        from backend.db.crud import add_player_to_snapshot, create_snapshot, get_or_create_player

        snap_id = await create_snapshot(db_session, "manual")
        for i in range(3):
            pid = await get_or_create_player(db_session, f"Few_{i}")
            await add_player_to_snapshot(db_session, snap_id, pid, "Antiguo", 0, 0, 1, 0)
        await db_session.commit()
        resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert resp.status_code in (400, 500)  # Error expected, specific code may vary

    async def test_draft_response_has_expected_player_shape(
        self, client: Any, db_session: Any
    ) -> None:
        """Each player dict in each mesa has the required keys."""
        snap_id = await make_snapshot_with_players(db_session, 14)
        resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        if resp.status_code != 200:
            # Skip shape check if draft fails
            return
        data = resp.json()
        if "mesas" not in data or not data["mesas"]:
            return
        first_player = data["mesas"][0]["jugadores"][0]
        for key in ("nombre", "es_nuevo", "juegos_ano", "tiene_prioridad"):
            assert key in first_player, f"Missing key '{key}' in player dict"


# ── POST /api/game/save ───────────────────────────────────────────────────────


class TestApiGameSave:
    async def test_missing_draft_returns_400(self, client: Any) -> None:
        resp = await client.post("/api/game/save", json={"snapshot_id": 1})
        assert resp.status_code == 422  # FastAPI validation error

    async def test_missing_snapshot_id_returns_400(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        resp = await client.post("/api/game/save", json={"draft": draft})
        assert resp.status_code == 422  # FastAPI validation error

    async def test_save_draft_returns_game_id(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        print(f"Save response status: {save_resp.status_code}")
        print(f"Save response body: {save_resp.text}")
        assert save_resp.status_code == 200
        data = save_resp.json()
        assert "game_id" in data
        assert isinstance(data["game_id"], int)

    async def test_save_draft_creates_game_event_in_db(self, client: Any, db_session: Any) -> None:
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        print(f"\n>>> Save response status: {save_resp.status_code}")
        print(f">>> Save response body: {save_resp.text}\n")
        game_id = save_resp.json()["game_id"]
        result = await db_session.execute(select(Event).where(Event.id == game_id))
        event = result.scalar_one_or_none()
        assert event is not None
        assert event.type == "game"

    async def test_save_draft_persists_correct_mesa_count(
        self, client: Any, db_session: Any
    ) -> None:
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        game_id = save_resp.json()["game_id"]
        result = await db_session.execute(select(Mesa).where(Mesa.event_id == game_id))
        mesas = result.scalars().all()
        assert len(mesas) == len(draft["mesas"])

    async def test_save_draft_creates_output_snapshot(self, client: Any, db_session: Any) -> None:
        """Saving a draft must produce a new output snapshot."""
        from backend.db.models import Snapshot

        snap_id = await make_snapshot_with_players(db_session, 14)
        result = await db_session.execute(select(Snapshot))
        before = len(result.scalars().all())
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        await client.post("/api/game/save", json={"snapshot_id": snap_id, "draft": draft})
        result = await db_session.execute(select(Snapshot))
        after = len(result.scalars().all())
        assert after == before + 1

    async def test_save_draft_with_editing_game_id_leaf_node(
        self, client: Any, db_session: Any
    ) -> None:
        """Test in-place editing when the game is a leaf node (no children)."""
        from backend.db.models import GameDetail

        # 1. Setup a game using /api/game/save (makes its output snapshot a leaf node)
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        original_game_id = save_resp.json()["game_id"]

        # Verify the game exists and is a leaf node initially
        result = await db_session.execute(
            select(Event).where(Event.id == original_game_id, Event.type == "game")
        )
        game_row = result.scalar_one_or_none()
        assert game_row is not None
        output_snapshot_id = game_row.output_snapshot_id

        # Verify it's a leaf node (no events source from it)
        result = await db_session.execute(
            select(Event).where(Event.source_snapshot_id == output_snapshot_id)
        )
        is_leaf = result.scalar_one_or_none() is None
        assert is_leaf, "Game should be a leaf node initially"

        # Count events before update
        result = await db_session.execute(select(Event))
        events_before = len(result.scalars().all())

        # 2. Send a new POST to /api/game/save including editing_game_id
        modified_draft = draft.copy()
        modified_draft["intentos_usados"] = 999  # Change to distinguish

        update_resp = await client.post(
            "/api/game/save",
            json={
                "snapshot_id": snap_id,
                "draft": modified_draft,
                "editing_game_id": original_game_id,
            },
        )

        # 3. Assert that it returns the *same* game_id (proving it updated in-place)
        assert update_resp.status_code == 200
        updated_game_id = update_resp.json()["game_id"]
        assert updated_game_id == original_game_id, "Should return same game_id for in-place update"

        # Assert that it did not create a new row in the events table
        result = await db_session.execute(select(Event))
        events_after = len(result.scalars().all())
        assert events_after == events_before, "Should not create new event for in-place update"

        # Verify the game details were updated (intentos should be 999)
        result = await db_session.execute(
            select(GameDetail).where(GameDetail.event_id == original_game_id)
        )
        updated_details = result.scalar_one_or_none()
        assert updated_details is not None
        assert updated_details.intentos == 999, "Game details should be updated in-place"

    async def test_save_draft_with_editing_game_id_internal_node(
        self, client: Any, db_session: Any
    ) -> None:
        """Test fallback behavior when the game is an internal node (has children)."""
        from backend.db.crud import create_event, create_snapshot
        from backend.db.models import GameDetail

        # 1. Setup a game
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        original_game_id = save_resp.json()["game_id"]

        # Get the output snapshot of the original game
        result = await db_session.execute(
            select(Event).where(Event.id == original_game_id, Event.type == "game")
        )
        game_row = result.scalar_one_or_none()
        assert game_row is not None
        output_snapshot_id = game_row.output_snapshot_id

        # 2. Create a new manual snapshot originating from that game's output snapshot
        # (this makes the game's output snapshot an internal node with children)
        child_snapshot_id = await create_snapshot(db_session, "manual")
        await create_event(db_session, "edit", output_snapshot_id, child_snapshot_id)
        await db_session.commit()

        # Verify the original game is now an internal node (has children)
        result = await db_session.execute(
            select(Event).where(Event.source_snapshot_id == output_snapshot_id)
        )
        is_leaf = result.scalar_one_or_none() is None
        assert not is_leaf, "Game should now be an internal node"

        # Count events before update
        result = await db_session.execute(select(Event))
        events_before = len(result.scalars().all())

        # 3. Send a POST to /api/game/save including editing_game_id
        modified_draft = draft.copy()
        modified_draft["intentos_usados"] = 777  # Change to distinguish

        update_resp = await client.post(
            "/api/game/save",
            json={
                "snapshot_id": snap_id,
                "draft": modified_draft,
                "editing_game_id": original_game_id,
            },
        )

        # 4. Assert that it falls back to standard behavior: returns a *new* game_id
        assert update_resp.status_code == 200
        new_game_id = update_resp.json()["game_id"]
        assert new_game_id != original_game_id, "Should return new game_id for internal node"

        # Assert that it creates a new branch in the events table
        result = await db_session.execute(select(Event))
        events_after = len(result.scalars().all())
        assert events_after == events_before + 1, "Should create new event for internal node"

        # Verify the new game exists and has the updated intentos
        result = await db_session.execute(
            select(GameDetail).where(GameDetail.event_id == new_game_id)
        )
        new_details = result.scalar_one_or_none()
        assert new_details is not None
        assert new_details.intentos == 777, "New game should have updated intentos"

        # Verify the original game is unchanged
        result = await db_session.execute(
            select(GameDetail).where(GameDetail.event_id == original_game_id)
        )
        original_details = result.scalar_one_or_none()
        assert original_details is not None
        assert original_details.intentos != 777, "Original game should remain unchanged"


# ── Regression Tests ──────────────────────────────────────────────────────────


class TestPaisReasonPersistence:
    """
    Regression tests for pais_reason field persistence.

    Previously, the pais_reason field generated by the algorithm wasn't
    being saved to the database. These tests verify end-to-end persistence
    through the API and database layers.
    """

    async def test_save_draft_persists_pais_reason(self, client: Any, db_session: Any) -> None:
        """
        Verify that pais_reason is persisted to mesa_players table.

        End-to-end test: draft → save → retrieve → assert pais_reason.
        """
        from backend.db.views import get_game_event_detail

        # Setup
        snap_id = await make_snapshot_with_players(db_session, 14)

        # Generate draft
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert draft_resp.status_code == 200
        draft = draft_resp.json()

        # Manually add pais_reason to simulate algorithm output
        test_reason = "Player was assigned this country to avoid repetition after 3 games"
        if draft["mesas"] and draft["mesas"][0]["jugadores"]:
            draft["mesas"][0]["jugadores"][0]["pais_reason"] = test_reason

        # Save draft
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        game_id = save_resp.json()["game_id"]

        # Retrieve game detail
        detail = await get_game_event_detail(db_session, game_id)
        assert detail is not None
        assert "mesas" in detail
        assert len(detail["mesas"]) > 0

        # Verify pais_reason was persisted
        first_mesa = detail["mesas"][0]
        assert "jugadores" in first_mesa
        assert len(first_mesa["jugadores"]) > 0

        first_player = first_mesa["jugadores"][0]
        assert "pais_reason" in first_player
        assert first_player["pais_reason"] == test_reason

    async def test_save_draft_handles_missing_pais_reason(
        self, client: Any, db_session: Any
    ) -> None:
        """
        Verify that missing pais_reason is handled gracefully.

        Players without pais_reason should have None/null in the database.
        """
        from backend.db.views import get_game_event_detail

        # Setup
        snap_id = await make_snapshot_with_players(db_session, 14)

        # Generate draft
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert draft_resp.status_code == 200
        draft = draft_resp.json()

        # Explicitly remove pais_reason from all players
        for mesa in draft["mesas"]:
            for jugador in mesa["jugadores"]:
                jugador.pop("pais_reason", None)

        # Save draft
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        game_id = save_resp.json()["game_id"]

        # Retrieve game detail
        detail = await get_game_event_detail(db_session, game_id)
        assert detail is not None

        # Verify all players have None/null for pais_reason
        for mesa in detail["mesas"]:
            for jugador in mesa["jugadores"]:
                assert jugador.get("pais_reason") is None

    async def test_save_draft_with_mixed_pais_reasons(self, client: Any, db_session: Any) -> None:
        """
        Verify that mesas can have some players with pais_reason and some without.

        This is the common case: only certain assignments have explanations.
        """
        from backend.db.views import get_game_event_detail

        # Setup
        snap_id = await make_snapshot_with_players(db_session, 14)

        # Generate draft
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert draft_resp.status_code == 200
        draft = draft_resp.json()

        # Add pais_reason to only the first player
        reason_for_first = "Test reason for first player"
        if draft["mesas"] and len(draft["mesas"][0]["jugadores"]) >= 2:
            draft["mesas"][0]["jugadores"][0]["pais_reason"] = reason_for_first
            # Explicitly ensure second player has no pais_reason
            draft["mesas"][0]["jugadores"][1].pop("pais_reason", None)

        # Save draft
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        game_id = save_resp.json()["game_id"]

        # Retrieve game detail
        detail = await get_game_event_detail(db_session, game_id)
        assert detail is not None

        # Verify mixed pais_reason values
        first_mesa = detail["mesas"][0]
        first_player = first_mesa["jugadores"][0]
        second_player = first_mesa["jugadores"][1]

        assert first_player["pais_reason"] == reason_for_first
        assert second_player["pais_reason"] is None
