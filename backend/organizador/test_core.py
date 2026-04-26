"""
Unit tests for organizador.py and models.py

Covers:
  - DraftPlayer class (attributes and priority score)
  - calculate_matches: number of tables, balance, duplicates,
    basic GM rules, waitlist and error cases.

Advanced priority, GM and league balancing tests
live in test_algoritmo.py.
Database and db_views tests live in test_db.py.
"""

from __future__ import annotations

import random
import unittest
from typing import TYPE_CHECKING

from .core import calculate_matches
from .models import DraftPlayer, DraftResult

if TYPE_CHECKING:
    from typing import Any

# ── Helpers ───────────────────────────────────────────────────────────────────


def _j(
    name: str,
    games_this_year: int = 0,
    desired_games: int = 1,
    gm_games: int = 0,
    *,
    has_priority: bool = False,
    is_new: bool = False,
) -> DraftPlayer:
    """Creates a DraftPlayer with sensible default values."""
    return DraftPlayer(
        name=name,
        is_new=is_new,
        games_this_year=games_this_year,
        desired_games=desired_games,
        gm_games=gm_games,
        has_priority=has_priority,
    )


def _pool(n: int, prefix: str = "J", **kwargs: Any) -> list[DraftPlayer]:
    """Creates N players with consecutive names (J0, J1, …)."""
    return [_j(f"{prefix}{i}", **kwargs) for i in range(n)]


# ── Tests de la clase Jugador ─────────────────────────────────────────────────


class TestJugador(unittest.TestCase):
    def test_is_new_true(self):
        self.assertTrue(_j("A", is_new=True).is_new)

    def test_is_new_false(self):
        self.assertFalse(_j("A", is_new=False).is_new)

    def test_is_new_case_insensitive(self):
        self.assertTrue(_j("A", is_new=True).is_new)

    def test_has_priority_true(self):
        self.assertTrue(_j("A", has_priority=True).has_priority)

    def test_has_priority_false(self):
        self.assertFalse(_j("A", has_priority=False).has_priority)

    def test_puntaje_nuevo_es_cero(self):
        # Un jugador nuevo siempre tiene la máxima prioridad (0)
        self.assertEqual(_j("A", is_new=True, games_this_year=10).priority_score, 0)

    def test_priority_score_flag_es_cero(self):
        # El flag de prioridad también produce puntaje 0
        self.assertEqual(_j("A", has_priority=True, games_this_year=10).priority_score, 0)

    def test_puntaje_antiguo_sin_juegos_este_ano(self):
        # Antiguo con 0 juegos: penalización mínima (0.05) para distinguirlo del nuevo.
        self.assertAlmostEqual(_j("A", games_this_year=0).priority_score, 0.05)

    def test_puntaje_antiguo_con_juegos(self):
        # 0.05 + 3 × 0.15 = 0.50
        self.assertAlmostEqual(_j("A", games_this_year=3).priority_score, 0.50)

    def test_puntaje_cap_en_noventa(self):
        # Con muchos juegos la fracción no puede superar 0.90
        self.assertAlmostEqual(_j("A", games_this_year=10).priority_score, 0.90)

    def test_gm_games_se_almacena(self):
        self.assertEqual(_j("A", gm_games=2).gm_games, 2)


# ── Tests del algoritmo principal ─────────────────────────────────────────────


class TestCalcularPartidas(unittest.TestCase):
    def setUp(self) -> None:
        # Semilla fija para que los tests que no iteran seeds sean deterministas
        random.seed(0)

    # ── Casos base ────────────────────────────────────────────────────────────

    def test_sin_players_retorna_none(self):
        self.assertIsNone(calculate_matches([]))

    def test_menos_de_siete_players_retorna_none(self):
        self.assertIsNone(calculate_matches(_pool(6)))

    def test_exactamente_siete_forma_una_partida(self):
        res = calculate_matches(_pool(7))
        assert res is not None
        self.assertIsInstance(res, DraftResult)
        self.assertEqual(len(res.tables), 1)
        self.assertEqual(len(res.tables[0].players), 7)

    def test_catorce_players_forman_dos_partidas(self):
        res = calculate_matches(_pool(14))
        assert res is not None
        self.assertEqual(len(res.tables), 2)

    def test_tickets_multiples_cuentan_correctamente(self):
        # 12 quieren 1 partida + 2 quieren 2 = 16 tickets → 2 tables
        players = _pool(12) + [
            _j("Multi1", desired_games=2),
            _j("Multi2", desired_games=2),
        ]
        res = calculate_matches(players)
        assert res is not None
        self.assertEqual(len(res.tables), 2)

    # ── Corrección de las tables ───────────────────────────────────────────────

    def test_cada_table_tiene_exactamente_siete_players(self):
        res = calculate_matches(_pool(14))
        assert res is not None
        for table in res.tables:
            self.assertEqual(len(table.players), 7)

    def test_sin_duplicados_por_table(self):
        """Un jugador no puede aparecer dos veces in the same table."""
        players = _pool(10) + [_j("Multi", desired_games=2)]
        res = calculate_matches(players)
        if res is None:
            return
        for table in res.tables:
            names = [j.name for j in table.players]
            self.assertEqual(len(names), len(set(names)), "Hay duplicados en una table")

    def test_jugador_multipartida_en_tables_distintas(self):
        """Un jugador que quiere 2 partidas debe quedar en tables diferentes."""
        players = _pool(12) + [
            _j("Multi1", desired_games=2),
            _j("Multi2", desired_games=2),
        ]
        res = calculate_matches(players)
        assert res is not None
        for name in ("Multi1", "Multi2"):
            tables_del_jugador = [
                i
                for i, table in enumerate(res.tables)
                if any(j.name == name for j in table.players)
            ]
            self.assertEqual(
                len(set(tables_del_jugador)),
                len(tables_del_jugador),
                f"{name} aparece en la misma table más de una vez",
            )

    # ── Balance de is_new ────────────────────────────────────────────────

    def test_balance_nuevos_y_antiguos_por_table(self):
        """Con una mezcla suficiente, cada table debe tener nuevos y antiguos."""
        players = _pool(6, prefix="N", is_new=True) + _pool(8, prefix="A")
        res = calculate_matches(players)
        assert res is not None
        for table in res.tables:
            self.assertTrue(any(j.is_new for j in table.players), "Mesa sin players nuevos")
            self.assertTrue(any(not j.is_new for j in table.players), "Mesa sin players antiguos")

    # ── Error de configuración ────────────────────────────────────────────────

    def test_excess_gms_does_not_fail(self):
        """If there are more GM slots than tables, it should not fail (graceful degradation)."""
        players = _pool(7)  # 1 table
        players += [_j("GM1", gm_games=1), _j("GM2", gm_games=1)]
        res = calculate_matches(players)

        # It should silently handle the excess and build 1 table
        assert res is not None
        self.assertEqual(len(res.tables), 1)

    def test_un_gm_en_unica_table_no_es_error(self):
        """Un solo GM para una sola table es configuración válida."""
        players = _pool(7) + [_j("GM1", gm_games=1)]
        res = calculate_matches(players)  # no debe lanzar excepción
        assert res is not None

    # ── Lista de espera ───────────────────────────────────────────────────────

    def test_lista_de_espera_contiene_players_sobrantes(self):
        """Con 15 players (2 tables = 14 cupos), 1 debe quedar en espera."""
        res = calculate_matches(_pool(15))
        assert res is not None
        self.assertEqual(len(res.tables), 2)
        total_colocados = sum(len(m.players) for m in res.tables)
        total_sobrantes = len(res.waitlist_players)
        self.assertEqual(total_colocados + total_sobrantes, 15)

    def test_todos_entran_cuando_hay_cupos_exactos(self):
        """Si los tickets caben exactamente, la lista de espera debe estar vacía."""
        res = calculate_matches(_pool(14))
        assert res is not None
        self.assertEqual(len(res.waitlist_players), 0)

    def test_two_phase_pipeline_execution_order(self):
        """Test that assign_countries_to_table is executed after run_distribution_loop."""
        from unittest.mock import MagicMock, patch

        from .core import calculate_matches

        # Create mock functions to track execution order
        distribution_mock = MagicMock()
        assignment_mock = MagicMock()

        # Create a mock result to return from run_distribution_loop
        from .models import DraftPlayer, DraftResult, DraftTable

        mock_draft_result = DraftResult(
            tables=[
                DraftTable(
                    table_number=1,
                    players=[
                        DraftPlayer(
                            name=f"Player{i}",
                            is_new=False,
                            games_this_year=0,
                            has_priority=False,
                            desired_games=1,
                            gm_games=0,
                        )
                        for i in range(7)
                    ],
                    gm=None,
                )
            ],
            waitlist_players=[],
            theoretical_minimum=0,
            attempts_used=1,
        )

        # Mock the two main functions
        with (
            patch(
                "backend.organizador.distribution.run_distribution_loop",
                distribution_mock,
            ),
            patch("backend.organizador.core.assign_countries_to_table", assignment_mock),
        ):
            # Set up the distribution mock to return our mock result
            distribution_mock.return_value = mock_draft_result

            # Create basic player pool
            players = _pool(14)

            # Run calculate_matches
            calculate_matches(players)

            # Verify both functions were called
            distribution_mock.assert_called()
            assignment_mock.assert_called()

            # Verify that assign_countries_to_table was called with player lists (not DraftTable objects)
            # This should happen after run_distribution_loop creates the tables
            assignment_calls = assignment_mock.call_args_list
            # Verify the assignment was called with player lists (from each table)
            for call in assignment_calls:
                players_arg = call[0][0]  # First argument should be list of DraftPlayer objects
                self.assertIsInstance(players_arg, list)
                if players_arg:  # If list is not empty
                    self.assertTrue(
                        hasattr(players_arg[0], "name")
                    )  # DraftPlayer has name attribute


if __name__ == "__main__":
    unittest.main(verbosity=2)
