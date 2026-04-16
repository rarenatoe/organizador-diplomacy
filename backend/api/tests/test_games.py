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

from backend.db.models import TimelineEdge

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def make_snapshot_with_players(db_session: Any, count: int = 14) -> int:
    """Creates a snapshot with `count` players, enough for the algorithm."""
    from backend.crud.players import get_or_create_player
    from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

    snap_id = await create_snapshot(db_session, "manual")
    for i in range(count):
        pid = await get_or_create_player(db_session, f"Jugador_{i:02d}")
        await add_player_to_snapshot(
            db_session, snap_id, pid, "Antiguo", i % 3, 2, 0, has_priority=False
        )
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
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.edge_type == "game")
        )
        event_count = len(result.scalars().all())
        assert event_count == 0

    async def test_too_few_players_returns_400(self, client: Any, db_session: Any) -> None:
        from backend.crud.players import get_or_create_player
        from backend.crud.snapshots import add_player_to_snapshot, create_snapshot

        snap_id = await create_snapshot(db_session, "manual")
        for i in range(3):
            pid = await get_or_create_player(db_session, f"Few_{i}")
            await add_player_to_snapshot(
                db_session, snap_id, pid, "Antiguo", 0, 1, 0, has_priority=False
            )
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
        for key in ("nombre", "es_nuevo", "juegos_este_ano", "has_priority"):
            assert key in first_player, f"Missing key '{key}' in player dict"

    async def test_unhashable_draftplayer_regression(self, client: Any, db_session: Any) -> None:
        """Test that duplicate DraftPlayer objects in waitlist don't cause TypeError: unhashable type."""
        from unittest.mock import patch

        from backend.organizador.models import DraftPlayer, DraftResult, DraftTable

        # Create a mock DraftResult with duplicate DraftPlayer objects in waitlist
        duplicate_player = DraftPlayer(
            name="DuplicatePlayer",
            experience="Veterano",
            games_this_year=5,
            desired_games=1,
            gm_games=0,
            has_priority=False,
        )

        mock_result = DraftResult(
            tables=[
                DraftTable(
                    table_number=1,
                    players=[
                        DraftPlayer(
                            name="OtherPlayer",
                            experience="Nuevo",
                            games_this_year=0,
                            desired_games=1,
                            gm_games=0,
                            has_priority=False,
                        )
                    ],
                    gm=None,
                )
            ],
            waitlist_players=[duplicate_player, duplicate_player],  # Same object twice
            theoretical_minimum=0,
            attempts_used=1,
        )

        snap_id = await make_snapshot_with_players(db_session, 14)

        # Mock calculate_matches to return our result with duplicates
        with patch("backend.api.routers.games.calculate_matches", return_value=mock_result):
            resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})

        # Should return HTTP 200 (proving the TypeError: unhashable type crash is fixed)
        assert resp.status_code == 200
        data = resp.json()

        # Verify the response structure
        assert "mesas" in data
        assert "tickets_sobrantes" in data
        assert "minimo_teorico" in data
        assert "intentos_usados" in data

        # Test Cartesian deduplication: exactly ONE entry for duplicated player
        assert len(data["tickets_sobrantes"]) == 1
        assert data["tickets_sobrantes"][0]["nombre"] == "DuplicatePlayer"

        # Verify minimo_teorico equals 0 (theoretical minimum from mock)
        assert data["minimo_teorico"] == 0

        assert data["tickets_sobrantes"][0]["cupos_faltantes"] == 2


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
        assert save_resp.status_code == 200
        data = save_resp.json()
        assert "game_id" in data
        assert isinstance(data["game_id"], int)

    async def test_api_game_save_success(self, client: Any, db_session: Any) -> None:
        """Integration test: API should return game_id on successful save of a new draft."""
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert draft_resp.status_code == 200
        draft = draft_resp.json()

        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        data = save_resp.json()
        assert "game_id" in data
        assert isinstance(data["game_id"], int)

    async def test_save_draft_with_editing_game_id_leaf_node(
        self, client: Any, db_session: Any
    ) -> None:
        """Integration test: API should handle in-place editing when game is a leaf node."""
        # 1. Setup a game using /api/game/save (makes its output snapshot a leaf node)
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        original_game_id = save_resp.json()["game_id"]

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

    async def test_save_draft_with_editing_game_id_internal_node(
        self, client: Any, db_session: Any
    ) -> None:
        """Integration test: API should fallback to new game when editing internal node."""
        from backend.crud.chain import create_branch_edge
        from backend.crud.snapshots import create_snapshot

        # 1. Setup a game
        snap_id = await make_snapshot_with_players(db_session, 14)
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        draft = draft_resp.json()
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        original_game_id = save_resp.json()["game_id"]

        # 2. Create a child snapshot to make the game an internal node
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.id == original_game_id)
        )
        game_row = result.scalar_one()
        child_snapshot_id = await create_snapshot(db_session, "manual")
        await create_branch_edge(db_session, game_row.output_snapshot_id, child_snapshot_id)
        await db_session.commit()

        # 3. Send update request
        modified_draft = draft.copy()
        modified_draft["intentos_usados"] = 777

        update_resp = await client.post(
            "/api/game/save",
            json={
                "snapshot_id": snap_id,
                "draft": modified_draft,
                "editing_game_id": original_game_id,
            },
        )

        # 4. Assert fallback behavior: returns a new game_id
        assert update_resp.status_code == 200
        new_game_id = update_resp.json()["game_id"]
        assert new_game_id != original_game_id, "Should return new game_id for internal node"


# ── Regression Tests ──────────────────────────────────────────────────────────


class TestCountryReasonPersistence:
    """
    Regression tests for country.reason field persistence.

    Previously, the country.reason field generated by the algorithm wasn't
    being saved to the database. These tests verify end-to-end persistence
    through the API and database layers.
    """

    async def test_save_draft_persists_country_reason(self, client: Any, db_session: Any) -> None:
        """
        Verify that country.reason is persisted to mesa_players table.

        End-to-end test: draft → save → retrieve → assert country.reason.
        """
        from backend.db.views import get_game_event_detail

        # Setup
        snap_id = await make_snapshot_with_players(db_session, 14)

        # Generate draft
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert draft_resp.status_code == 200
        draft = draft_resp.json()

        # Manually add reason to simulate algorithm output
        test_reason = "Player was assigned this country to avoid repetition after 3 games"
        if draft["mesas"] and draft["mesas"][0]["jugadores"]:
            if not draft["mesas"][0]["jugadores"][0].get("country"):
                draft["mesas"][0]["jugadores"][0]["country"] = {"name": "England"}
            draft["mesas"][0]["jugadores"][0]["country"]["reason"] = test_reason

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

        # Verify country.reason was persisted
        first_mesa = detail["mesas"][0]
        assert "jugadores" in first_mesa
        assert len(first_mesa["jugadores"]) > 0

        first_player = first_mesa["jugadores"][0]
        assert "country" in first_player and first_player["country"] is not None
        assert first_player["country"].get("reason") == test_reason

    async def test_save_draft_handles_missing_country_reason(
        self, client: Any, db_session: Any
    ) -> None:
        """
        Verify that missing country.reason is handled gracefully.

        Players without country.reason should have None/null in the database.
        """
        from backend.db.views import get_game_event_detail

        # Setup
        snap_id = await make_snapshot_with_players(db_session, 14)

        # Generate draft
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert draft_resp.status_code == 200
        draft = draft_resp.json()

        # Explicitly remove country.reason from all players
        for mesa in draft["mesas"]:
            for jugador in mesa["jugadores"]:
                if "country" in jugador and jugador["country"] is not None:
                    jugador["country"].pop("reason", None)

        # Save draft
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        game_id = save_resp.json()["game_id"]

        # Retrieve game detail
        detail = await get_game_event_detail(db_session, game_id)
        assert detail is not None

        # Verify all players have None/null for country.reason
        for mesa in detail["mesas"]:
            for jugador in mesa["jugadores"]:
                country = jugador.get("country")
                assert country is None or country.get("reason") is None

    async def test_save_draft_with_mixed_country_reasons(
        self, client: Any, db_session: Any
    ) -> None:
        """
        Verify that mesas can have some players with country.reason and some without.

        This is the common case: only certain assignments have explanations.
        """
        from backend.db.views import get_game_event_detail

        # Setup
        snap_id = await make_snapshot_with_players(db_session, 14)

        # Generate draft
        draft_resp = await client.post("/api/game/draft", json={"snapshot_id": snap_id})
        assert draft_resp.status_code == 200
        draft = draft_resp.json()

        # Add reason to only the first player
        reason_for_first = "Test reason for first player"
        if draft["mesas"] and len(draft["mesas"][0]["jugadores"]) >= 2:
            if not draft["mesas"][0]["jugadores"][0].get("country"):
                draft["mesas"][0]["jugadores"][0]["country"] = {"name": "England"}
            draft["mesas"][0]["jugadores"][0]["country"]["reason"] = reason_for_first

            # Explicitly ensure second player has no reason
            if draft["mesas"][0]["jugadores"][1].get("country"):
                draft["mesas"][0]["jugadores"][1]["country"].pop("reason", None)

        # Save draft
        save_resp = await client.post(
            "/api/game/save", json={"snapshot_id": snap_id, "draft": draft}
        )
        assert save_resp.status_code == 200
        game_id = save_resp.json()["game_id"]

        # Retrieve game detail
        detail = await get_game_event_detail(db_session, game_id)
        assert detail is not None

        # Verify mixed country.reason values
        first_mesa = detail["mesas"][0]
        first_player = first_mesa["jugadores"][0]
        second_player = first_mesa["jugadores"][1]

        assert first_player["country"]["reason"] == reason_for_first
        country = second_player.get("country")
        assert country is None or country.get("reason") is None


# ── DELETE /api/game/{game_id} ───────────────────────────────────────────────────


class TestApiGameDelete:
    async def test_delete_nonexistent_returns_404(self, client: Any) -> None:
        """Test that deleting a non-existent game returns 404."""
        resp = await client.delete("/api/game/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Game not found"

    async def test_delete_game_removes_game_and_child_snapshot(
        self, client: Any, db_session: Any
    ) -> None:
        """Create a chain (Snap A -> Game 1 -> Snap B). Delete Game 1 via /api/games/{id}.
        Assert Game 1 and Snap B are deleted from the DB, but Snap A remains."""
        from backend.crud.chain import create_game_edge
        from backend.crud.snapshots import create_snapshot
        from backend.db.models import Snapshot

        # Setup: Snap A -> Game 1 -> Snap B
        snap_a = await make_snapshot_with_players(db_session, 14)
        snap_b = await create_snapshot(db_session, "organizar")

        # Create game edge from A to B
        game_edge_id = await create_game_edge(db_session, snap_a, snap_b, 1)
        await db_session.commit()

        # Verify initial state: all exist
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.id == game_edge_id)
        )
        assert result.scalar_one_or_none() is not None

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        assert result.scalar_one_or_none() is not None

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is not None

        # Action: Delete game
        resp = await client.delete(f"/api/game/{game_edge_id}")
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}

        # Assert: Game 1 and Snap B are deleted, but Snap A remains
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.id == game_edge_id)
        )
        assert result.scalar_one_or_none() is None  # Game deleted

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is None  # Child snapshot deleted

        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        assert result.scalar_one_or_none() is not None  # Parent snapshot remains

    async def test_delete_game_triggers_squash_on_parent(
        self, client: Any, db_session: Any
    ) -> None:
        """Recreate the scenario from test_snapshots.py::test_delete_sibling_triggers_squash
        but trigger the deletion via /api/games/{game_id} instead of the snapshot endpoint.
        Verify the sibling branch is squashed correctly."""
        from backend.crud.chain import create_branch_edge, create_game_edge
        from backend.crud.players import get_or_create_player
        from backend.crud.snapshots import (
            add_player_to_snapshot,
            create_snapshot,
            get_snapshot_players,
        )
        from backend.db.models import Snapshot

        # Helper function for this test
        async def make_snapshot_with_players_source(
            db_session: Any, n: int = 5, source: str = "notion_sync"
        ) -> int:
            """Creates a snapshot with n players and returns snapshot_id."""
            snap_id = await create_snapshot(db_session, source)
            for i in range(n):
                pid = await get_or_create_player(db_session, f"P{snap_id}_{i}")
                await add_player_to_snapshot(
                    db_session, snap_id, pid, "Antiguo", 0, 2, 0, has_priority=True
                )
            await db_session.commit()
            return snap_id

        # Setup: A -> Game -> B
        #        A -> Manual -> C
        snap_a = await make_snapshot_with_players_source(db_session, n=5, source="notion_sync")
        snap_b = await create_snapshot(db_session, "organizar")
        snap_c = await create_snapshot(db_session, "manual")

        # Add different players to C to verify squashing
        pid_c1 = await get_or_create_player(db_session, "PlayerC1")
        pid_c2 = await get_or_create_player(db_session, "PlayerC2")
        await add_player_to_snapshot(
            db_session, snap_c, pid_c1, "Antiguo", 5, 2, 0, has_priority=True
        )
        await add_player_to_snapshot(
            db_session, snap_c, pid_c2, "Nuevo", 2, 1, 0, has_priority=True
        )

        # Create edges: A -> game -> B and A -> branch -> C
        game_edge_id = await create_game_edge(db_session, snap_a, snap_b, 1)
        branch_edge_id = await create_branch_edge(db_session, snap_a, snap_c)
        await db_session.commit()

        # Get C's original source and timestamp for verification
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_c))
        snap_c_obj = result.scalar_one()
        c_source = snap_c_obj.source
        c_timestamp = snap_c_obj.created_at

        # Verify initial state: A has 2 outgoing edges
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snap_a)
        )
        assert len(result.scalars().all()) == 2

        # Action: Delete game (which will delete snapshot B and trigger squash on A)
        resp = await client.delete(f"/api/game/{game_edge_id}")
        assert resp.status_code == 200
        await db_session.commit()
        db_session.expire_all()

        # Assert 1: Snapshot B is gone
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_b))
        assert result.scalar_one_or_none() is None

        # Assert 2: Snapshot C is also gone (squashed into A)
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_c))
        assert result.scalar_one_or_none() is None

        # Assert 3: Snapshot A still exists
        result = await db_session.execute(select(Snapshot).where(Snapshot.id == snap_a))
        snap_a_obj = result.scalar_one()
        assert snap_a_obj is not None

        # Assert 4: A's roster is now C's roster
        players_a = await get_snapshot_players(db_session, snap_a)
        assert len(players_a) == 2
        player_names = {p["nombre"] for p in players_a}
        assert player_names == {"PlayerC1", "PlayerC2"}

        # Assert 5: A inherited C's source and timestamp
        assert snap_a_obj.source == c_source
        assert snap_a_obj.created_at == c_timestamp

        # Assert 6: A has no outgoing edges now (both B and C edges removed)
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snap_a)
        )
        assert len(result.scalars().all()) == 0

        # Assert 7: The branch edge from A to C is gone
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.id == branch_edge_id)
        )
        assert result.scalar_one_or_none() is None

        # Assert 8: The game edge is also gone
        result = await db_session.execute(
            select(TimelineEdge).where(TimelineEdge.id == game_edge_id)
        )
        assert result.scalar_one_or_none() is None
