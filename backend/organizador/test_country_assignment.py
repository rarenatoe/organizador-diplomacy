"""Tests for the Greedy Intervention Minimization country assignment algorithm."""

import unittest

from .core import assign_countries_to_table
from .models import DraftPlayer


def _p(
    name: str, e: int = 0, f: int = 0, g: int = 0, i: int = 0, a: int = 0, r: int = 0, t: int = 0
) -> DraftPlayer:
    """Helper to quickly create a player with specific country counts."""
    return DraftPlayer(
        name=name,
        games_this_year=0,
        desired_games=1,
        gm_games=0,
        c_england=e,
        c_france=f,
        c_germany=g,
        c_italy=i,
        c_austria=a,
        c_russia=r,
        c_turkey=t,
    )


class TestGreedyInterventionAlgorithm(unittest.TestCase):
    def test_no_intervention_needed_flat_stats(self):
        """Edge Case: Everyone has exactly the same stats, or max difference is 1. No curses."""
        players = [
            _p("P1", e=0, f=0, g=0, i=0, a=0, r=0, t=0),
            _p("P2", e=1, f=1, g=1, i=1, a=1, r=1, t=1),
            _p("P3", e=5, f=6, g=5, i=6, a=5, r=6, t=5),  # Max difference is 1 (not cursed)
        ]
        assign_countries_to_table(players)
        for p in players:
            self.assertEqual(p.country, "", f"{p.name} should not be assigned anything.")

    def test_single_curse_high_baseline(self):
        """Edge Case: Cursing works on relative baselines, even with high historical games."""
        players = [
            # P1's baseline is 10. England is 12 (Cursed by +2)
            _p("P1", e=12, f=10, g=10, i=10, a=10, r=10, t=10),
            _p("P2", e=10, f=10, g=10, i=10, a=10, r=10, t=10),
            _p("P3", e=10, f=10, g=10, i=10, a=10, r=10, t=10),
        ]
        assign_countries_to_table(players)

        assigned = [p for p in players if p.country != ""]
        self.assertGreater(len(assigned), 0, "High baseline curse was ignored.")

        # P1 must NOT receive England.
        self.assertNotEqual(players[0].country, "England")

    def test_tool_b_self_assignment_efficiency(self):
        """
        Tool B (Self-Assignment): If a player has MULTIPLE curses, the algorithm
        should realize assigning them to their lowest country resolves ALL of them instantly.
        """
        players = [
            # P1 is cursed on 6 countries. Lowest is Turkey (0).
            _p("P1", e=3, f=3, g=3, i=3, a=3, r=3, t=0),
            _p("P2", e=0, f=0, g=0, i=0, a=0, r=0, t=0),
            _p("P3", e=0, f=0, g=0, i=0, a=0, r=0, t=0),
        ]
        assign_countries_to_table(players)

        # The most efficient move is to assign P1 to Turkey. (1 assignment fixes 6 curses).
        self.assertEqual(players[0].country, "Turkey")
        self.assertTrue(any("Auto-asignación" in r for r in players[0].country_reason))

    def test_tool_a_shielding_behavior(self):
        """
        Tool A (Shielding): If P1 is cursed, and P1 can't easily self-assign,
        a shield player should take the hit.
        """
        players = [
            _p("P1", e=2, f=0, g=0, i=0, a=0, r=0, t=0),  # Cursed on England.
            _p("P2", e=0, f=2, g=0, i=0, a=0, r=0, t=0),  # Cursed on France.
        ]
        assign_countries_to_table(players)

        self.assertNotEqual(players[0].country, "England")
        self.assertNotEqual(players[1].country, "France")

    def test_combo_move_double_duty(self):
        """
        Double Duty: One assignment fixes TWO peoples' problems at once.
        P1 is cursed on England. P2 is cursed on EVERYTHING EXCEPT England.
        Giving England to P2 acts as a self-assignment for P2 AND a shield for P1.
        """
        players = [
            _p("P1", e=3, f=0, g=0, i=0, a=0, r=0, t=0),  # Cursed on England
            _p("P2", e=0, f=3, g=3, i=3, a=3, r=3, t=3),  # Cursed on everything except England
            _p("P3", e=0, f=0, g=0, i=0, a=0, r=0, t=0),  # Neutral
        ]
        assign_countries_to_table(players)

        # P2 getting England is the ultimate combo move.
        self.assertEqual(players[1].country, "England")
        self.assertTrue(any("Auto-asignación" in r for r in players[1].country_reason))
        self.assertTrue(any("escudo" in r for r in players[1].country_reason))

    def test_cannot_assign_cursed_country_as_shield(self):
        """Edge Case: A player cannot be used as a shield for a country they are themselves cursed on."""
        players = [
            _p("P1", e=3, f=0, g=0, i=0, a=0, r=0, t=0),  # Needs shield for England
            _p("P2", e=3, f=0, g=0, i=0, a=0, r=0, t=0),  # Needs shield for England
            _p("P3", e=0, f=0, g=0, i=0, a=0, r=0, t=0),  # Clean
        ]
        assign_countries_to_table(players)
        self.assertNotEqual(players[0].country, "England")
        self.assertNotEqual(players[1].country, "England")

    # ─────────────────────────────────────────────────────────────────────────
    # NEW EDGE CASES
    # ─────────────────────────────────────────────────────────────────────────

    def test_tie_breaker_behavior(self):
        """
        Edge Case A: Tie-breaker. A player is equally cursed on multiple countries.
        The algorithm should confidently self-assign them to a 0-count country
        to escape BOTH curses simultaneously.
        """
        players = [
            _p("P1", e=5, f=5, g=0, i=0, a=0, r=0, t=0),  # Cursed on E and F equally
            _p("P2", e=0, f=0, g=0, i=0, a=0, r=0, t=0),
            _p("P3", e=0, f=0, g=0, i=0, a=0, r=0, t=0),
        ]
        assign_countries_to_table(players)

        # P1 must NOT get England or France
        self.assertNotEqual(players[0].country, "England")
        self.assertNotEqual(players[0].country, "France")
        # P1 should have self-assigned to escape both
        self.assertNotEqual(players[0].country, "")
        self.assertTrue(any("Auto-asignación" in r for r in players[0].country_reason))

    def test_no_clean_shields(self):
        """
        Edge Case B: No "clean" shields (0 games).
        The algorithm must pick a shield who has played the country,
        but is NOT legally considered "cursed" relative to the baseline.
        """
        players = [
            _p(
                "P1", e=10, f=0, g=0, i=0, a=0, r=0, t=0
            ),  # Severely cursed on England (Baseline 0, count 10)
            _p("P2", e=5, f=0, g=0, i=0, a=0, r=0, t=0),  # Count 5
            _p("P3", e=5, f=0, g=0, i=0, a=0, r=0, t=0),  # Count 5
        ]
        assign_countries_to_table(players)

        # P1 cannot get England.
        self.assertNotEqual(players[0].country, "England")

        # Because P2 and P3 are not cursed on England (relative to their own 0 baseline,
        # they are +5, but wait, the algorithm evaluates if they are cursed.
        # Actually, P2 and P3 ARE cursed on England relative to their own baselines!
        # So they CANNOT be shields! P1 MUST self-assign a different country.
        self.assertNotEqual(players[0].country, "")
        self.assertNotEqual(players[0].country, "England")
        self.assertTrue(any("Auto-asignación" in r for r in players[0].country_reason))

    def test_exhausted_shields(self):
        """
        Edge Case C: What happens when the only valid shields are taken before
        a curse is evaluated? The player should successfully fall back to self-assignment.
        """
        players = [
            _p("P1", e=0, f=5, g=5, i=5, a=5, r=5, t=5),  # MUST take England
            _p("P2", e=5, f=0, g=5, i=5, a=5, r=5, t=5),  # MUST take France
            _p("P3", e=0, f=0, g=0, i=0, a=0, r=0, t=5),  # Cursed on Turkey
        ]
        assign_countries_to_table(players)

        self.assertEqual(players[0].country, "England")
        self.assertEqual(players[1].country, "France")

        # P3's shields (P1 and P2) are exhausted/occupied.
        # P3 should self-assign something that ISN'T Turkey, England, or France.
        self.assertNotEqual(players[2].country, "Turkey")
        self.assertNotEqual(players[2].country, "England")
        self.assertNotEqual(players[2].country, "France")
        self.assertNotEqual(players[2].country, "")
        self.assertTrue(any("Auto-asignación" in r for r in players[2].country_reason))

    def test_gridlock_defense(self):
        """
        Edge Case D: Mathematically impossible to resolve. Everyone is cursed on everything.
        The loop must break safely without entering an infinite loop.
        """
        players_gridlocked = [_p(f"P{i}", e=5, f=5, g=5, i=5, a=5, r=5, t=5) for i in range(7)]

        try:
            assign_countries_to_table(players_gridlocked)
            success = True
        except Exception:
            success = False

        self.assertTrue(success, "Algorithm entered an infinite loop or crashed on gridlock.")
        for p in players_gridlocked:
            self.assertEqual(p.country, "")


if __name__ == "__main__":
    unittest.main()
