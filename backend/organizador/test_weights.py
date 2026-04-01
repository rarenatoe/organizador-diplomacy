"""
Unit tests for weights.py - build_weighted_tickets logic.
"""
import unittest

from .models import DraftPlayer
from .weights import build_weighted_tickets


def _j(name: str, d: int = 1, g: int = 0, exp: str = "Antiguo", j: int = 0):
    return DraftPlayer(
        name=name,
        experience=exp,
        games_this_year=j,
        priority="False",
        desired_games=d,
        gm_games=g,
    )

class TestWeights(unittest.TestCase):
    def test_build_weighted_tickets_basic(self):
        # 14 players, 1 ticket each -> 2 tables
        players = [_j(f"P{i}") for i in range(14)]
        estimated, actual, minimum, gms, tickets = build_weighted_tickets(players)
        
        self.assertEqual(estimated, 2)
        self.assertEqual(actual, 2)
        self.assertEqual(minimum, 0)
        self.assertEqual(len(tickets), 14)
        self.assertEqual(len(gms), 0)

    def test_build_weighted_tickets_with_gm(self):
        # 14 players, one is GM. 
        # Total tickets = 14. estimated_tables = 2.
        # GM slots = 1. OK.
        players = [_j(f"P{i}") for i in range(13)] + [_j("GM", g=1)]
        estimated, actual, minimum, gms, tickets = build_weighted_tickets(players)
        
        self.assertEqual(estimated, 2)
        self.assertEqual(actual, 2)
        self.assertEqual(minimum, 0)
        self.assertEqual(len(gms), 1)
        # GM has 1 ticket as player (default)
        self.assertEqual(len(tickets), 14)

    def test_error_too_many_gms(self):
        # 7 players -> 1 table. 2 GMs.
        players = [_j(f"P{i}") for i in range(5)] + [_j("GM1", g=1), _j("GM2", g=1)]
        with self.assertRaises(ValueError):
            build_weighted_tickets(players)

    def test_weight_calculation_logic(self):
        # Verify weights: new player (0.0) vs veteran (0.9)
        j_new = _j("New", exp="Nuevo")
        j_vet = _j("Vet", exp="Veteran", j=10)
        
        _, _, _, _, tickets = build_weighted_tickets([j_new, j_vet] * 7) # 14 tickets
        
        # Sort by weight as algorithm does
        tickets.sort(key=lambda t: t[0])
        
        # Weights for first slot: 
        # New: 1.0 + 0.0 = 1.0
        # Vet: 1.0 + 0.9 = 1.9
        self.assertEqual(tickets[0][0], 1.0)
        self.assertEqual(tickets[0][1].name, "New")
        self.assertEqual(tickets[-1][0], 1.9)
        self.assertEqual(tickets[-1][1].name, "Vet")

if __name__ == "__main__":
    unittest.main()
