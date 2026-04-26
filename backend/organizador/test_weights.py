"""
Unit tests for weights.py - build_weighted_tickets logic.
"""

import unittest

from .models import DraftPlayer
from .weights import build_weighted_tickets


def _j(name: str, d: int = 1, g: int = 0, j: int = 0, *, is_new: bool = False):
    return DraftPlayer(
        name=name,
        is_new=is_new,
        games_this_year=j,
        has_priority=False,
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

    def test_handle_too_many_gms(self):
        """Test that excess GMs are gracefully capped instead of raising an error."""
        # 7 players -> 1 table. 3 GMs competing for 1 slot.
        players = [_j(f"P{i}") for i in range(4)] + [
            _j("GM1", g=1, d=1),
            _j("GM2", g=1, d=1),
            _j("GM3", g=1, d=1),
        ]
        estimated, _, _, gms, _ = build_weighted_tickets(players)

        self.assertEqual(estimated, 1)
        self.assertEqual(len(gms), 1)  # Only 1 GM accepted
        self.assertEqual(gms[0].gm_games, 1)

        # The other 2 GMs should have their gm_games securely capped to 0
        capped_gms = [p for p in players if "GM" in p.name and p.gm_games == 0]
        self.assertEqual(len(capped_gms), 2)

    def test_prioritize_pure_gms(self):
        """Test that players who only want to GM (0 desired games) get priority."""
        # 8 players total. 7 want to play, 1 wants to only GM. -> 1 table. 1 slot available.
        # PlayerGM wants 1 game to play, 1 to GM.
        # PureGM wants 0 games to play, 1 to GM.
        players = [_j(f"P{i}") for i in range(6)] + [
            _j("PlayerGM", d=1, g=1),
            _j("PureGM", d=0, g=1),
        ]
        estimated, _, _, gms, _ = build_weighted_tickets(players)

        self.assertEqual(estimated, 1)
        self.assertEqual(len(gms), 1)

        # PureGM should win the slot because they have fewer desired_games
        self.assertEqual(gms[0].name, "PureGM")

        # Check that PlayerGM was gracefully capped
        player_gm = next(p for p in players if p.name == "PlayerGM")
        self.assertEqual(player_gm.gm_games, 0)

    def test_theoretical_minimum_never_negative(self):
        """Test that theoretical_minimum is calculated using max(0, ...) and never drops below 0."""
        # Oversaturate tables: 8 players requesting 1 game each
        # This should result in 1 table (7 players) with 1 left over
        players = [_j(f"P{i}", d=1) for i in range(8)]
        estimated, actual, minimum, gms, tickets = build_weighted_tickets(players)

        # Verify theoretical_minimum is never negative
        self.assertGreaterEqual(minimum, 0)

        # Since no players have gm_games, there should be no active GMs
        self.assertEqual(len(gms), 0)

        # With 8 players wanting 1 game each, we should have:
        # - 1 table (7 players)
        # - 1 player left over
        # - theoretical_minimum should be 1 (the leftover player)
        self.assertEqual(estimated, 1)
        self.assertEqual(actual, 1)
        self.assertEqual(minimum, 1)  # 1 player cannot be placed
        self.assertEqual(len(tickets), 8)

    def test_weight_calculation_logic(self):
        # Verify weights: new player (0.0) vs veteran (0.9)
        j_new = _j("New", is_new=True)
        j_vet = _j("Vet", is_new=False, j=10)

        _, _, _, _, tickets = build_weighted_tickets([j_new, j_vet] * 7)  # 14 tickets

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
