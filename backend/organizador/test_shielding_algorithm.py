"""Tests for new shielding country assignment algorithm."""

import unittest

from .core import assign_countries_to_mesa
from .models import Jugador


class TestShieldingAlgorithm(unittest.TestCase):
    """Test the new shielding country assignment algorithm."""

    def test_algorithm_runs_without_errors(self):
        """The algorithm should execute without throwing exceptions."""
        players = [
            Jugador(nombre="Alice", experiencia="Antiguo", juegos_ano=5, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=1, c_france=1, c_germany=1, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),
            Jugador(nombre="Bob", experiencia="Antiguo", juegos_ano=3, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=0, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),
            Jugador(nombre="Charlie", experiencia="Antiguo", juegos_ano=2, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=0, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),
        ]
        
        # This should not raise any exceptions
        try:
            assign_countries_to_mesa(players)
        except Exception as e:
            self.fail(f"Algorithm raised unexpected exception: {e}")

    def test_cursed_players_get_shields_assigned(self):
        """Players with country history should get shield assignments."""
        players = [
            Jugador(nombre="Alice", experiencia="Antiguo", juegos_ano=5, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=2, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),  # Cursed in England
            Jugador(nombre="Bob", experiencia="Antiguo", juegos_ano=1, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=0, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),  # Clean history
            Jugador(nombre="Charlie", experiencia="Antiguo", juegos_ano=1, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=0, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),  # Clean history
        ]
        
        assign_countries_to_mesa(players)
        
        # At least one player should have a country assigned (the shield)
        assigned_players = [p for p in players if p.pais != ""]
        self.assertGreater(len(assigned_players), 0, "At least one player should be assigned a country")

    def test_no_cursed_players_remain_unassigned(self):
        """Players without country history should remain unassigned."""
        players = [
            Jugador(nombre="Alice", experiencia="Antiguo", juegos_ano=5, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=1, c_france=1, c_germany=1, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),  # All countries 1 game
            Jugador(nombre="Bob", experiencia="Antiguo", juegos_ano=3, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=0, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),  # All countries 0 games
            Jugador(nombre="Charlie", experiencia="Antiguo", juegos_ano=2, prioridad="False", partidas_deseadas=1, partidas_gm=0,
                     c_england=0, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),  # All countries 0 games
        ]
        
        assign_countries_to_mesa(players)
        
        # All players should have no country assigned
        for player in players:
            self.assertEqual(player.pais, "", f"Player {player.nombre} should have no country assigned")

    def test_optimal_shield_selection_and_reason(self):
        """The algorithm must pick player with the lowest count for the cursed country."""
        players = [
            # Alice is cursed in England (2 games).
            Jugador(nombre="Alice", experiencia="Antiguo", juegos_ano=5, prioridad="False", partidas_deseadas=1, partidas_gm=0, c_england=2, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),
            # Bob has played England once (1 game).
            Jugador(nombre="Bob", experiencia="Antiguo", juegos_ano=3, prioridad="False", partidas_deseadas=1, partidas_gm=0, c_england=1, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),
            # Charlie has never played England (0 games).
            Jugador(nombre="Charlie", experiencia="Antiguo", juegos_ano=2, prioridad="False", partidas_deseadas=1, partidas_gm=0, c_england=0, c_france=0, c_germany=0, c_italy=0, c_austria=0, c_russia=0, c_turkey=0),
        ]
        
        assign_countries_to_mesa(players)
        
        # 1. Alice (cursed) should NOT get a country directly
        self.assertEqual(players[0].pais, "")
        # 2. Charlie (0 games) is a better shield than Bob (1 game)
        self.assertEqual(players[2].pais, "England", "Charlie should be picked as a shield for England")
        # 3. The reason should explicitly mention Alice and the count
        self.assertIsNotNone(players[2].pais_reason)
        self.assertIn("Alice", players[2].pais_reason or "")
        self.assertIn("2", players[2].pais_reason or "")
        # 4. Bob should be left alone
        self.assertEqual(players[1].pais, "")


if __name__ == "__main__":
    unittest.main()
