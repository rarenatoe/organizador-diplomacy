"""
Unit tests for distribution.py - run_distribution_loop and distribuir_tickets.
"""
from __future__ import annotations

import unittest

from .distribution import distribuir_tickets, run_distribution_loop
from .models import Jugador


def _j(nombre: str, d: int = 1, g: int = 0, exp: str = "Antiguo", j: int = 0) -> Jugador:
    return Jugador(
        nombre=nombre,
        experiencia=exp,
        juegos_ano=j,
        prioridad="False",
        partidas_deseadas=d,
        partidas_gm=g,
    )

class TestDistribution(unittest.TestCase):
    def test_distribuir_tickets_fills_tables(self):
        # 7 tickets for 1 table
        jugadores = [_j(f"P{i}") for i in range(7)]
        weighted = [(1.0 + float(i), j) for i, j in enumerate(jugadores)]
        partidas: list[list[Jugador]] = [[]]
        
        rechazados = distribuir_tickets(weighted, partidas, {}, es_grupo_nuevo=True)
        
        self.assertEqual(len(rechazados), 0)
        self.assertEqual(len(partidas[0]), 7)

    def test_distribuir_tickets_rejects_duplicates(self):
        # 2 tickets for same player, only 1 table. Must reject the second.
        j = _j("P1", d=2)
        weighted = [(1.0, j), (2.0, j)]
        partidas: list[list[Jugador]] = [[]]
        
        rechazados = distribuir_tickets(weighted, partidas, {}, es_grupo_nuevo=True)
        
        self.assertEqual(len(rechazados), 1)
        self.assertEqual(len(partidas[0]), 1)

    def test_run_distribution_loop_early_exit(self):
        # 14 players, perfect fit. theoretical minimum waitlist = 0.
        # Should exit quickly.
        jugadores = [_j(f"P{i}") for i in range(14)]
        weighted = [(1.0, j) for j in jugadores]
        
        res = run_distribution_loop(
            jugadores, weighted, [], 
            mesas_estimadas=2, mesas_reales=2, minimo_teorico=0
        )
        
        assert res is not None
        self.assertEqual(len(res.mesas), 2)
        self.assertEqual(len(res.tickets_sobrantes), 0)

    def test_gm_blocking_logic(self):
        # GM1 arbitrates Table 1 (index 0). 
        # Table 1 should NOT have GM1 as player.
        gm = _j("GM1", g=1, d=1)
        jugadores = [_j(f"P{i}") for i in range(13)] + [gm]
        # Weight for GM player ticket is 1.5 (0.5*g + slot_index 1.0)
        weighted = [(1.0, j) for j in jugadores[:-1]] + [(1.5, gm)]
        
        # Force GM1 to arbitrate Table 1
        res = run_distribution_loop(
            jugadores, weighted, [gm], 
            mesas_estimadas=2, mesas_reales=2, minimo_teorico=0
        )
        
        assert res is not None
        for mesa in res.mesas:
            if mesa.gm and mesa.gm.nombre == "GM1":
                player_names = [p.nombre for p in mesa.jugadores]
                self.assertNotIn("GM1", player_names)

if __name__ == "__main__":
    unittest.main()
