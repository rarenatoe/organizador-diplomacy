"""Tests for draft persistence logic."""

import unittest

from backend.db.db import add_player_to_snapshot, create_snapshot, get_db, get_snapshot_players
from backend.organizador.persistence import create_output_snapshot_from_draft


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


if __name__ == "__main__":
    unittest.main()
