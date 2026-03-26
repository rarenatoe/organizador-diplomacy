"""
Unit tests for weights.py - build_weighted_tickets logic.
"""
import unittest
from .models import Jugador
from .weights import build_weighted_tickets

def _j(nombre: str, d=1, g=0, exp="Antiguo", j=0):
    return Jugador(nombre, exp, j, "False", d, g)

class TestWeights(unittest.TestCase):
    def test_build_weighted_tickets_basic(self):
        # 14 players, 1 ticket each -> 2 tables
        jugadores = [_j(f"P{i}") for i in range(14)]
        estimadas, reales, minimo, gms, tickets = build_weighted_tickets(jugadores)
        
        self.assertEqual(estimadas, 2)
        self.assertEqual(reales, 2)
        self.assertEqual(minimo, 0)
        self.assertEqual(len(tickets), 14)
        self.assertEqual(len(gms), 0)

    def test_build_weighted_tickets_with_gm(self):
        # 14 players, one is GM. 
        # Total tickets = 14. mesas_estimadas = 2.
        # GM slots = 1. OK.
        jugadores = [_j(f"P{i}") for i in range(13)] + [_j("GM", g=1)]
        estimadas, reales, minimo, gms, tickets = build_weighted_tickets(jugadores)
        
        self.assertEqual(estimadas, 2)
        self.assertEqual(reales, 2)
        self.assertEqual(len(gms), 1)
        # GM has 1 ticket as player (default)
        self.assertEqual(len(tickets), 14)

    def test_error_too_many_gms(self):
        # 7 players -> 1 table. 2 GMs.
        jugadores = [_j(f"P{i}") for i in range(5)] + [_j("GM1", g=1), _j("GM2", g=1)]
        with self.assertRaises(ValueError):
            build_weighted_tickets(jugadores)

    def test_weight_calculation_logic(self):
        # Verify weights: new player (0.0) vs veteran (0.9)
        j_nuevo = _j("Nuevo", exp="Nuevo")
        j_vet = _j("Vet", exp="Antiguo", j=10)
        
        _, _, _, _, tickets = build_weighted_tickets([j_nuevo, j_vet] * 7) # 14 tickets
        
        # Sort by weight as the algorithm does
        tickets.sort(key=lambda t: t[0])
        
        # Weights for first slot: 
        # Nuevo: 1.0 + 0.0 = 1.0
        # Vet: 1.0 + 0.9 = 1.9
        self.assertEqual(tickets[0][0], 1.0)
        self.assertEqual(tickets[0][1].nombre, "Nuevo")
        self.assertEqual(tickets[-1][0], 1.9)
        self.assertEqual(tickets[-1][1].nombre, "Vet")

if __name__ == "__main__":
    unittest.main()
