"""Tests for draft persistence logic."""

import unittest

from backend.db.db import add_player_to_snapshot, create_snapshot, get_db, get_snapshot_players
from backend.organizador.persistence import (
    create_output_snapshot_from_draft,
    save_game_draft,
    update_game_draft,
)


class TestPersistence(unittest.TestCase):
    """Test draft persistence and player stat updates."""

    def setUp(self):
        """Set up in-memory database for each test."""
        self.conn = get_db(":memory:")
        self.input_snapshot_id = create_snapshot(self.conn, "notion_sync")
        add_player_to_snapshot(self.conn, self.input_snapshot_id, "Alice", "Antiguo", 5, 0, 2, 0)
        add_player_to_snapshot(self.conn, self.input_snapshot_id, "Bob", "Nuevo", 0, 0, 1, 0)
        add_player_to_snapshot(self.conn, self.input_snapshot_id, "Charlie", "Nuevo", 3, 0, 1, 0)
        self.conn.commit()

    def tearDown(self):
        """Clean up database connection."""
        self.conn.close()

    def test_players_in_mesas_get_games_incremented(self):
        """Players placed in mesas should have juegos_este_ano incremented by 1."""
        draft_data = {
            "mesas": [
                {
                    "numero": 1,
                    "jugadores": [
                        {
                            "nombre": "Alice",
                            "es_nuevo": False,
                            "juegos_ano": 5,
                            "tiene_prioridad": False,
                            "partidas_deseadas": 1,
                            "partidas_gm": 0,
                            "c_england": 1,
                            "c_france": 0,
                            "c_germany": 0,
                            "c_italy": 0,
                            "c_austria": 0,
                            "c_russia": 0,
                            "c_turkey": 0,
                            "pais": "England",
                        }
                    ]
                }
            ],
            "tickets_sobrantes": [],
        }
        
        # Create output snapshot from draft
        output_snapshot_id = create_output_snapshot_from_draft(
            self.conn, self.input_snapshot_id, draft_data
        )
        
        # Verify Alice's games were incremented
        updated_players = get_snapshot_players(self.conn, output_snapshot_id)
        alice_data = next(p for p in updated_players if p["nombre"] == "Alice")
        self.assertEqual(alice_data["juegos_este_ano"], 6, "Alice should have 6 games (5 + 1)")

    def test_nuevo_players_promoted_to_antiguo(self):
        """Players with experiencia == 'Nuevo' who are placed in mesas are promoted to 'Antiguo'."""
        draft_data = {
            "mesas": [
                {
                    "numero": 1,
                    "jugadores": [
                        {
                            "nombre": "Bob",
                            "es_nuevo": True,
                            "juegos_ano": 0,
                            "tiene_prioridad": False,
                            "partidas_deseadas": 1,
                            "partidas_gm": 0,
                            "c_england": 0,
                            "c_france": 0,
                            "c_germany": 0,
                            "c_italy": 0,
                            "c_austria": 0,
                            "c_russia": 0,
                            "c_turkey": 0,
                            "pais": "France",
                        }
                    ]
                }
            ],
            "tickets_sobrantes": [],
        }
        
        # Create output snapshot from draft
        output_snapshot_id = create_output_snapshot_from_draft(
            self.conn, self.input_snapshot_id, draft_data
        )
        
        # Verify Bob was promoted from "Nuevo" to "Antiguo"
        updated_players = get_snapshot_players(self.conn, output_snapshot_id)
        bob_data = next(p for p in updated_players if p["nombre"] == "Bob")
        self.assertEqual(bob_data["experiencia"], "Antiguo", "Bob should be promoted to Antiguo")

    def test_waiting_list_players_not_incremented(self):
        """Players in waiting list should NOT get their games incremented or experience changed."""
        draft_data = {
            "mesas": [],
            "tickets_sobrantes": [
                {
                    "nombre": "Charlie",
                    "es_nuevo": True,
                    "juegos_ano": 3,
                    "tiene_prioridad": False,
                    "partidas_deseadas": 2,
                    "partidas_gm": 0,
                    "c_england": 0,
                    "c_france": 0,
                    "c_germany": 0,
                    "c_italy": 0,
                    "c_austria": 0,
                    "c_russia": 0,
                    "c_turkey": 0,
                }
            ],
        }
        
        # Create output snapshot from draft
        output_snapshot_id = create_output_snapshot_from_draft(
            self.conn, self.input_snapshot_id, draft_data
        )
        
        # Verify Charlie's stats were NOT changed
        updated_players = get_snapshot_players(self.conn, output_snapshot_id)
        charlie_data = next(p for p in updated_players if p["nombre"] == "Charlie")
        self.assertEqual(charlie_data["juegos_este_ano"], 3, "Charlie's games should NOT be incremented")
        self.assertEqual(charlie_data["experiencia"], "Nuevo", "Charlie should remain Nuevo")

    def test_partidas_gm_reset_to_zero(self):
        """partidas_gm should be reset to 0 for all players in the resulting snapshot."""
        draft_data = {
            "mesas": [
                {
                    "numero": 1,
                    "jugadores": [
                        {
                            "nombre": "Alice",
                            "es_nuevo": False,
                            "juegos_ano": 5,
                            "tiene_prioridad": False,
                            "partidas_deseadas": 1,
                            "partidas_gm": 3,  # Alice was GM
                            "c_england": 1,
                            "c_france": 0,
                            "c_germany": 0,
                            "c_italy": 0,
                            "c_austria": 0,
                            "c_russia": 0,
                            "c_turkey": 0,
                            "pais": "England",
                        }
                    ]
                }
            ],
            "tickets_sobrantes": [],
        }
        
        # Create output snapshot from draft
        output_snapshot_id = create_output_snapshot_from_draft(
            self.conn, self.input_snapshot_id, draft_data
        )
        
        # Verify Alice's GM count was reset
        updated_players = get_snapshot_players(self.conn, output_snapshot_id)
        alice_data = next(p for p in updated_players if p["nombre"] == "Alice")
        self.assertEqual(alice_data["partidas_gm"], 0, "Alice's partidas_gm should be reset to 0")

    def test_update_game_draft_in_place(self):
        """Test updating an existing game draft in place."""
        # 1. Setup: Create a manual snapshot and save an initial game draft
        manual_snapshot_id = create_snapshot(self.conn, "manual")
        # Add players to manual snapshot
        add_player_to_snapshot(self.conn, manual_snapshot_id, "Alice", "Antiguo", 5, 0, 2, 0)
        add_player_to_snapshot(self.conn, manual_snapshot_id, "Bob", "Nuevo", 0, 0, 1, 0)
        add_player_to_snapshot(self.conn, manual_snapshot_id, "Charlie", "Antiguo", 3, 0, 1, 0)
        self.conn.commit()
        
        # Initial draft data
        initial_draft = {
            "mesas": [
                {
                    "numero": 1,
                    "jugadores": [
                        {
                            "nombre": "Alice",
                            "es_nuevo": False,
                            "juegos_ano": 5,
                            "tiene_prioridad": False,
                            "partidas_deseadas": 1,
                            "partidas_gm": 0,
                            "c_england": 1,
                            "c_france": 0,
                            "c_germany": 0,
                            "c_italy": 0,
                            "c_austria": 0,
                            "c_russia": 0,
                            "c_turkey": 0,
                            "pais": "England",
                        }
                    ]
                }
            ],
            "tickets_sobrantes": [
                {
                    "nombre": "Bob",
                    "es_nuevo": True,
                    "juegos_ano": 0,
                    "tiene_prioridad": False,
                    "partidas_deseadas": 1,
                    "partidas_gm": 0,
                    "c_england": 0,
                    "c_france": 0,
                    "c_germany": 0,
                    "c_italy": 0,
                    "c_austria": 0,
                    "c_russia": 0,
                    "c_turkey": 0,
                }
            ],
            "intentos_usados": 2,
        }
        
        # Save initial game draft
        game_id = save_game_draft(self.conn, manual_snapshot_id, initial_draft)
        self.conn.commit()
        
        # Get the output snapshot ID for later use
        game_event_row = self.conn.execute(
            "SELECT output_snapshot_id FROM events WHERE id = ?", (game_id,)
        ).fetchone()
        output_snapshot_id = game_event_row["output_snapshot_id"]
        
        # Verify initial state
        initial_mesas = self.conn.execute(
            "SELECT COUNT(*) as count FROM mesas WHERE event_id = ?", (game_id,)
        ).fetchone()["count"]
        self.assertEqual(initial_mesas, 1)
        
        initial_waiting = self.conn.execute(
            "SELECT COUNT(*) as count FROM waiting_list WHERE event_id = ?", (game_id,)
        ).fetchone()["count"]
        self.assertEqual(initial_waiting, 1)
        
        initial_intentos = self.conn.execute(
            "SELECT intentos FROM game_details WHERE event_id = ?", (game_id,)
        ).fetchone()["intentos"]
        self.assertEqual(initial_intentos, 2)
        
        # 2. Action: Update the game draft with modified data
        updated_draft = {
            "mesas": [
                {
                    "numero": 1,
                    "jugadores": [
                        {
                            "nombre": "Charlie",  # Changed player
                            "es_nuevo": False,
                            "juegos_ano": 3,
                            "tiene_prioridad": False,
                            "partidas_deseadas": 1,
                            "partidas_gm": 0,
                            "c_england": 0,
                            "c_france": 1,
                            "c_germany": 0,
                            "c_italy": 0,
                            "c_austria": 0,
                            "c_russia": 0,
                            "c_turkey": 0,
                            "pais": "France",
                        },
                        {
                            "nombre": "Alice",  # Alice moved to different seat
                            "es_nuevo": False,
                            "juegos_ano": 5,
                            "tiene_prioridad": False,
                            "partidas_deseadas": 1,
                            "partidas_gm": 0,
                            "c_england": 1,
                            "c_france": 0,
                            "c_germany": 0,
                            "c_italy": 0,
                            "c_austria": 0,
                            "c_russia": 0,
                            "c_turkey": 0,
                            "pais": "England",
                        }
                    ]
                }
            ],
            "tickets_sobrantes": [
                {
                    "nombre": "Bob",  # Bob still on waiting list
                    "es_nuevo": True,
                    "juegos_ano": 0,
                    "tiene_prioridad": False,
                    "partidas_deseadas": 1,
                    "partidas_gm": 0,
                    "c_england": 0,
                    "c_france": 0,
                    "c_germany": 0,
                    "c_italy": 0,
                    "c_austria": 0,
                    "c_russia": 0,
                    "c_turkey": 0,
                }
            ],
            "intentos_usados": 5,  # Different intentos
        }
        
        # Update the game draft
        updated_game_id = update_game_draft(
            self.conn, game_id, manual_snapshot_id, output_snapshot_id, updated_draft
        )
        self.conn.commit()
        
        # 3. Assertions: Verify the update worked correctly
        
        # Verify game_id remained the same
        self.assertEqual(updated_game_id, game_id)
        
        # Verify game_details reflects the new intentos
        updated_intentos = self.conn.execute(
            "SELECT intentos FROM game_details WHERE event_id = ?", (game_id,)
        ).fetchone()["intentos"]
        self.assertEqual(updated_intentos, 5, "intentos should be updated to 5")
        
        # Verify old mesas and waiting_list were deleted and replaced
        updated_mesas = self.conn.execute(
            "SELECT COUNT(*) as count FROM mesas WHERE event_id = ?", (game_id,)
        ).fetchone()["count"]
        self.assertEqual(updated_mesas, 1, "Should still have 1 mesa")
        
        updated_waiting = self.conn.execute(
            "SELECT COUNT(*) as count FROM waiting_list WHERE event_id = ?", (game_id,)
        ).fetchone()["count"]
        self.assertEqual(updated_waiting, 1, "Should still have 1 waiting list entry")
        
        # Verify the mesa players were updated (Charlie added, Alice moved)
        mesa_players = self.conn.execute(
            """
            SELECT p.nombre, mp.orden, mp.pais
            FROM mesa_players mp
            JOIN players p ON mp.player_id = p.id
            JOIN mesas m ON mp.mesa_id = m.id
            WHERE m.event_id = ?
            ORDER BY mp.orden
            """,
            (game_id,)
        ).fetchall()
        
        self.assertEqual(len(mesa_players), 2, "Should have 2 players in mesa")
        self.assertEqual(mesa_players[0]["nombre"], "Charlie", "Charlie should be first")
        self.assertEqual(mesa_players[0]["orden"], 1)
        self.assertEqual(mesa_players[0]["pais"], "France")
        self.assertEqual(mesa_players[1]["nombre"], "Alice", "Alice should be second")
        self.assertEqual(mesa_players[1]["orden"], 2)
        self.assertEqual(mesa_players[1]["pais"], "England")
        
        # Verify output_snapshot_id remained the exact same
        same_output_snapshot_id = self.conn.execute(
            "SELECT output_snapshot_id FROM events WHERE id = ?", (game_id,)
        ).fetchone()["output_snapshot_id"]
        self.assertEqual(same_output_snapshot_id, output_snapshot_id, "output_snapshot_id should remain unchanged")
        
        # Verify the output snapshot roster was updated to reflect the new draft
        updated_players = get_snapshot_players(self.conn, output_snapshot_id)
        players_by_name = {p["nombre"]: p for p in updated_players}
        
        # Alice should have juegos_este_ano incremented (she played)
        alice_data = players_by_name["Alice"]
        self.assertEqual(alice_data["juegos_este_ano"], 6, "Alice should have 6 games (5 + 1)")
        self.assertEqual(alice_data["prioridad"], 0, "Alice should not be on waiting list")
        
        # Charlie should have juegos_este_ano incremented (he played)
        charlie_data = players_by_name["Charlie"]
        self.assertEqual(charlie_data["juegos_este_ano"], 4, "Charlie should have 4 games (3 + 1)")
        self.assertEqual(charlie_data["prioridad"], 0, "Charlie should not be on waiting list")
        
        # Bob should remain on waiting list (priority = 1)
        bob_data = players_by_name["Bob"]
        self.assertEqual(bob_data["juegos_este_ano"], 0, "Bob should not have games incremented")
        self.assertEqual(bob_data["prioridad"], 1, "Bob should be on waiting list")
        self.assertEqual(bob_data["experiencia"], "Nuevo", "Bob should remain Nuevo")


if __name__ == "__main__":
    unittest.main()
