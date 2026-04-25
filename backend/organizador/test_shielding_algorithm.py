"""Tests for new shielding country assignment algorithm."""

import unittest

from .core import assign_countries_to_table
from .models import DraftPlayer


class TestShieldingAlgorithm(unittest.TestCase):
    """Test the new shielding country assignment algorithm."""

    def test_algorithm_runs_without_errors(self):
        """The algorithm should execute without throwing exceptions."""
        players = [
            DraftPlayer(
                name="Alice",
                is_new=False,
                games_this_year=5,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=1,
                c_france=1,
                c_germany=1,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),
            DraftPlayer(
                name="Bob",
                is_new=False,
                games_this_year=3,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),
            DraftPlayer(
                name="Charlie",
                is_new=False,
                games_this_year=2,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),
        ]

        # This should not raise any exceptions
        try:
            assign_countries_to_table(players)
        except Exception as e:
            self.fail(f"Algorithm raised unexpected exception: {e}")

    def test_cursed_players_get_shields_assigned(self):
        """Players with country history should get shield assignments."""
        players = [
            DraftPlayer(
                name="Alice",
                is_new=False,
                games_this_year=5,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=2,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),  # Cursed in England
            DraftPlayer(
                name="Bob",
                is_new=False,
                games_this_year=1,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),  # Clean history
            DraftPlayer(
                name="Charlie",
                is_new=False,
                games_this_year=1,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),  # Clean history
        ]

        assign_countries_to_table(players)

        # At least one player should have a country assigned (the shield)
        assigned_players = [p for p in players if p.country != ""]
        self.assertGreater(
            len(assigned_players), 0, "At least one player should be assigned a country"
        )

    def test_no_cursed_players_remain_unassigned(self):
        """Players without country history should remain unassigned."""
        players = [
            DraftPlayer(
                name="Alice",
                is_new=False,
                games_this_year=5,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=1,
                c_france=1,
                c_germany=1,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),  # All countries 1 game
            DraftPlayer(
                name="Bob",
                is_new=False,
                games_this_year=3,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),  # All countries 0 games
            DraftPlayer(
                name="Charlie",
                is_new=False,
                games_this_year=2,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),  # All countries 0 games
        ]

        assign_countries_to_table(players)

        # All players should have no country assigned
        for player in players:
            self.assertEqual(
                player.country, "", f"Player {player.name} should have no country assigned"
            )

    def test_optimal_shield_selection_and_reason(self):
        """The algorithm must pick player with the lowest count for cursed country."""
        players = [
            # Alice is cursed in England (2 games).
            DraftPlayer(
                name="Alice",
                is_new=False,
                games_this_year=5,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=2,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),
            # Bob has played England once (1 game).
            DraftPlayer(
                name="Bob",
                is_new=False,
                games_this_year=3,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=1,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),
            # Charlie has never played England (0 games).
            DraftPlayer(
                name="Charlie",
                is_new=False,
                games_this_year=2,
                has_priority=False,
                desired_games=1,
                gm_games=0,
                c_england=0,
                c_france=0,
                c_germany=0,
                c_italy=0,
                c_austria=0,
                c_russia=0,
                c_turkey=0,
            ),
        ]

        assign_countries_to_table(players)

        # 1. Alice (cursed) should NOT get a country directly
        self.assertEqual(players[0].country, "")
        # 2. Charlie (0 games) is a better shield than Bob (1 game)
        self.assertEqual(
            players[2].country, "England", "Charlie should be picked as a shield for England"
        )
        # 3. The reason should explicitly mention Alice and count
        self.assertNotEqual(players[2].country_reason, "")
        self.assertIn("Alice", players[2].country_reason)
        self.assertIn("2", players[2].country_reason)
        # 4. Bob should be left alone
        self.assertEqual(players[1].country, "")


if __name__ == "__main__":
    unittest.main()
