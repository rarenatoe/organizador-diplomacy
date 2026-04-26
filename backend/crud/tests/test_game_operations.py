"""
test_games.py — Tests for game draft CRUD operations.

Tests the async CRUD functions save_game_draft and update_game_draft
in backend/crud/games.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from backend.crud.chain import create_game_edge
from backend.crud.games import (
    add_table_player,
    create_game_table,
    save_game_draft,
    update_game_draft,
)
from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
    get_snapshot_players,
)
from backend.db.models import Player, Snapshot, SnapshotSource, TablePlayer, TimelineEdge

pytestmark = pytest.mark.asyncio

# Type annotation for draft data
DraftData = dict[str, Any]


class TestGameDraftOperations:
    """Tests for save_game_draft and update_game_draft CRUD operations."""

    async def test_save_game_draft_creates_complete_game_structure(self, db_session: Any) -> None:
        """save_game_draft should create game event, tables, players, and waiting list."""
        # Setup: Create input snapshot with players
        input_snap = await create_snapshot(db_session, SnapshotSource.MANUAL)

        # Create players
        pid1 = await get_or_create_player(db_session, "Alice")
        pid2 = await get_or_create_player(db_session, "Bob")
        pid3 = await get_or_create_player(db_session, "Charlie")
        pid4 = await get_or_create_player(db_session, "David")

        # Add players to input snapshot
        await add_player_to_snapshot(
            db_session, input_snap, pid1, 5, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid2, 0, 1, 0, has_priority=True, is_new=True
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid3, 3, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid4, 0, 1, 0, has_priority=True, is_new=True
        )
        await db_session.commit()

        # Draft data: 2 tables, 2 waiting list spots
        draft_data: DraftData = {
            "intentos_usados": 2,
            "mesas": [
                {
                    "numero": 1,
                    "gm": {"nombre": "Alice"},
                    "jugadores": [
                        {"nombre": "Bob", "country": {"name": "England", "reason": "Available"}},
                        {"nombre": "Charlie", "country": {"name": "France", "reason": "Shielding"}},
                    ],
                },
                {
                    "numero": 2,
                    "gm": None,
                    "jugadores": [
                        {"nombre": "David", "country": {"name": "Germany", "reason": "Available"}}
                    ],
                },
            ],
            "tickets_sobrantes": [{"nombre": "Alice"}, {"nombre": "Bob"}],
        }

        # Action: Save game draft
        game_id = await save_game_draft(db_session, input_snap, draft_data)
        await db_session.commit()

        # Verify: Game event created
        assert game_id is not None
        result = await db_session.execute(select(TimelineEdge).where(TimelineEdge.id == game_id))
        game_event = result.scalar_one()
        assert game_event.edge_type == "game"
        assert game_event.source_snapshot_id == input_snap

        # Verify: Output snapshot created
        output_snap = await db_session.execute(
            select(Snapshot).where(Snapshot.id == game_event.output_snapshot_id)
        )
        output_snap_obj = output_snap.scalar_one()
        assert output_snap_obj.source == "organizar"

        # Verify: Tables created with correct players
        tables_result = await db_session.execute(select(TablePlayer))
        table_players = tables_result.scalars().all()
        assert len(table_players) == 3  # 2 players in table 1, 1 in table 2

        # Verify: Country reason was saved
        reasons = {tp.country_reason for tp in table_players if tp.country_reason}
        assert "Shielding" in reasons
        assert "Available" in reasons

    async def test_save_game_draft_handles_empty_draft(self, db_session: Any) -> None:
        """save_game_draft should handle draft with no tables or waiting list."""
        # Setup
        input_snap = await create_snapshot(db_session, SnapshotSource.MANUAL)
        pid = await get_or_create_player(db_session, "Alice")
        await add_player_to_snapshot(
            db_session, input_snap, pid, 5, 2, 0, has_priority=True, is_new=False
        )
        await db_session.commit()

        # Empty draft
        draft_data: DraftData = {"intentos_usados": 0, "mesas": [], "tickets_sobrantes": []}

        # Action
        game_id = await save_game_draft(db_session, input_snap, draft_data)
        await db_session.commit()

        # Verify: Game event created
        assert game_id is not None
        result = await db_session.execute(select(TimelineEdge).where(TimelineEdge.id == game_id))
        game_event = result.scalar_one()
        assert game_event.edge_type == "game"

        # Verify: Output snapshot created with updated player is_new
        output_players = await get_snapshot_players(db_session, game_event.output_snapshot_id)
        assert len(output_players) == 1
        assert output_players[0].juegos_este_ano == 5  # No games played, should remain same

    async def test_update_game_draft_deletes_and_recreates_structure(self, db_session: Any) -> None:
        """update_game_draft should delete existing tables/waiting list and recreate."""
        # Setup: Create initial game
        input_snap = await create_snapshot(db_session, SnapshotSource.MANUAL)
        output_snap = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)

        pid1 = await get_or_create_player(db_session, "Alice")
        pid2 = await get_or_create_player(db_session, "Bob")

        await add_player_to_snapshot(
            db_session, input_snap, pid1, 5, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid2, 0, 1, 0, has_priority=True, is_new=True
        )
        await add_player_to_snapshot(
            db_session, output_snap, pid1, 6, 2, 0, has_priority=False, is_new=False
        )  # Played 1 game
        await add_player_to_snapshot(
            db_session, output_snap, pid2, 1, 1, 0, has_priority=False, is_new=False
        )  # Played 1 game
        await db_session.commit()

        game_id = await create_game_edge(db_session, input_snap, output_snap, 1)

        # Create initial table
        table_id = await create_game_table(db_session, game_id, 1)
        await add_table_player(db_session, table_id, pid1, 1, "England")
        await db_session.commit()

        # Verify initial state
        result = await db_session.execute(
            select(TablePlayer).where(TablePlayer.table_id == table_id)
        )
        initial_players = result.scalars().all()
        assert len(initial_players) == 1

        # New draft data - different structure
        new_draft_data: DraftData = {
            "intentos_usados": 3,
            "mesas": [
                {
                    "numero": 1,
                    "gm": {"nombre": "Bob"},
                    "jugadores": [
                        {"nombre": "Alice", "country": {"name": "France", "reason": "Updated"}},
                        {"nombre": "Bob", "country": {"name": "Germany", "reason": "GM playing"}},
                    ],
                }
            ],
            "tickets_sobrantes": [],
        }

        # Action: Update game draft
        # Expunge objects from the session to simulate a fresh HTTP request and prevent
        # identity map conflicts from raw SQL DELETEs overlapping with new INSERTs.
        db_session.expunge_all()
        updated_game_id = await update_game_draft(
            db_session, game_id, input_snap, output_snap, new_draft_data
        )
        await db_session.commit()

        # Verify: Same game ID returned
        assert updated_game_id == game_id

        # Verify: Old table players deleted, new ones created
        result = await db_session.execute(select(TablePlayer))
        all_table_players = result.scalars().all()
        assert len(all_table_players) == 2  # 2 new players

        # Verify: Countries updated
        countries = {tp.country for tp in all_table_players}
        assert countries == {"France", "Germany"}

    async def test_update_game_draft_raw_sql_delete_operations(self, db_session: Any) -> None:
        """Regression test: verify raw SQL DELETE statements work correctly."""
        # Setup: Create game with complex structure
        input_snap = await create_snapshot(db_session, SnapshotSource.MANUAL)
        output_snap = await create_snapshot(db_session, SnapshotSource.ORGANIZAR)

        pid1 = await get_or_create_player(db_session, "Alice")
        pid2 = await get_or_create_player(db_session, "Bob")
        pid3 = await get_or_create_player(db_session, "Charlie")

        # Add players to snapshots
        await add_player_to_snapshot(
            db_session, input_snap, pid1, 5, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid2, 0, 1, 0, has_priority=True, is_new=True
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid3, 3, 2, 0, has_priority=True, is_new=False
        )

        await add_player_to_snapshot(
            db_session, output_snap, pid1, 6, 2, 0, has_priority=False, is_new=False
        )
        await add_player_to_snapshot(
            db_session, output_snap, pid2, 1, 1, 0, has_priority=False, is_new=False
        )
        await add_player_to_snapshot(
            db_session, output_snap, pid3, 4, 2, 0, has_priority=False, is_new=False
        )
        await db_session.commit()

        game_id = await create_game_edge(db_session, input_snap, output_snap, 1)

        # Create multiple tables with players
        table1_id = await create_game_table(db_session, game_id, 1)
        table2_id = await create_game_table(db_session, game_id, 2)

        await add_table_player(db_session, table1_id, pid1, 1, "England")
        await add_table_player(db_session, table1_id, pid2, 2, "France")
        await add_table_player(db_session, table2_id, pid3, 1, "Germany")
        await db_session.commit()

        # Verify initial state - should have 3 table players
        result = await db_session.execute(select(TablePlayer))
        initial_players = result.scalars().all()
        assert len(initial_players) == 3

        # Draft that completely changes the structure
        new_draft_data: DraftData = {
            "intentos_usados": 2,
            "mesas": [
                {
                    "numero": 1,
                    "gm": None,
                    "jugadores": [
                        {"nombre": "Charlie", "country": {"name": "Italy", "reason": "Only player"}}
                    ],
                }
            ],
            "tickets_sobrantes": [{"nombre": "Alice"}, {"nombre": "Bob"}],
        }

        # Action: Update with completely different structure
        await update_game_draft(db_session, game_id, input_snap, output_snap, new_draft_data)
        await db_session.commit()

        # Verify: All old table players deleted
        result = await db_session.execute(select(TablePlayer))
        final_players = result.scalars().all()
        assert len(final_players) == 1  # Only 1 new player

        # Verify: The new player is Charlie with Italy
        new_player = final_players[0]
        result = await db_session.execute(select(Player).where(Player.id == new_player.player_id))
        player_obj = result.scalar_one()
        assert player_obj.name == "Charlie"
        assert new_player.country == "Italy"

    async def test_create_output_snapshot_from_draft_promotes_players(
        self, db_session: Any
    ) -> None:
        """_create_output_snapshot_from_draft should promote Nuevo players who play games."""
        # Setup: Create input snapshot with mix of Nuevo and Antiguo players
        input_snap = await create_snapshot(db_session, SnapshotSource.MANUAL)

        pid_nuevo = await get_or_create_player(db_session, "NewPlayer")
        pid_antiguo = await get_or_create_player(db_session, "OldPlayer")
        pid_not_playing = await get_or_create_player(db_session, "IdlePlayer")

        await add_player_to_snapshot(
            db_session, input_snap, pid_nuevo, 0, 1, 0, has_priority=True, is_new=True
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid_antiguo, 5, 2, 0, has_priority=True, is_new=False
        )
        await add_player_to_snapshot(
            db_session, input_snap, pid_not_playing, 0, 1, 0, has_priority=True, is_new=True
        )
        await db_session.commit()

        # Draft where Nuevo player plays, becomes Antiguo
        draft_data: DraftData = {
            "mesas": [
                {
                    "numero": 1,
                    "gm": None,
                    "jugadores": [
                        {"nombre": "NewPlayer", "pais": "England"},
                        {"nombre": "OldPlayer", "pais": "France"},
                    ],
                }
            ],
            "tickets_sobrantes": [{"nombre": "IdlePlayer"}],
        }

        # Action: Save game (this calls _create_output_snapshot_from_draft internally)
        game_id = await save_game_draft(db_session, input_snap, draft_data)
        await db_session.commit()

        # Verify: Get output snapshot
        result = await db_session.execute(select(TimelineEdge).where(TimelineEdge.id == game_id))
        game_event = result.scalar_one()

        output_players = await get_snapshot_players(db_session, game_event.output_snapshot_id)
        output_player_data = {p.nombre: p for p in output_players}

        # Verify: NewPlayer promoted to Antiguo, played 1 game
        assert not output_player_data["NewPlayer"].is_new
        assert output_player_data["NewPlayer"].juegos_este_ano == 1

        # Verify: OldPlayer remains Antiguo, played 1 more game
        assert not output_player_data["OldPlayer"].is_new
        assert output_player_data["OldPlayer"].juegos_este_ano == 6

        # Verify: IdlePlayer remains Nuevo, didn't play, in waitlist
        assert output_player_data["IdlePlayer"].is_new
        assert output_player_data["IdlePlayer"].juegos_este_ano == 0
        assert output_player_data["IdlePlayer"].has_priority  # In waitlist
