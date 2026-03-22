"""
Tests de unidad para organizador.py y models.py

Cubre:
  - Clase Jugador (atributos y puntaje de prioridad)
  - _calcular_partidas: número de mesas, balance, duplicados,
    reglas de GM básicas, lista de espera y casos de error.

Los tests avanzados de prioridad, GM y balanceo de liga
viven en test_algoritmo.py.
Los tests de db.py y db_views.py viven en test_db.py.
"""
import random
import unittest

from .organizador import Jugador, ResultadoPartidas, _calcular_partidas


# ── Helpers ───────────────────────────────────────────────────────────────────

def _j(
    nombre: str,
    experiencia: str = "Antiguo",
    juegos_ano: int = 0,
    prioridad: str = "False",
    partidas_deseadas: int = 1,
    partidas_gm: int = 0,
) -> Jugador:
    """Crea un Jugador con valores por defecto sensatos."""
    return Jugador(nombre, experiencia, juegos_ano, prioridad, partidas_deseadas, partidas_gm)


def _pool(n: int, prefix: str = "J", **kwargs) -> list[Jugador]:
    """Crea N jugadores con nombres consecutivos (J0, J1, …)."""
    return [_j(f"{prefix}{i}", **kwargs) for i in range(n)]


# ── Tests de la clase Jugador ─────────────────────────────────────────────────

class TestJugador(unittest.TestCase):

    def test_es_nuevo_true(self):
        self.assertTrue(_j("A", experiencia="Nuevo").es_nuevo)

    def test_es_nuevo_false(self):
        self.assertFalse(_j("A", experiencia="Antiguo").es_nuevo)

    def test_es_nuevo_case_insensitive(self):
        self.assertTrue(_j("A", experiencia="NUEVO").es_nuevo)

    def test_tiene_prioridad_true(self):
        self.assertTrue(_j("A", prioridad="True").tiene_prioridad)

    def test_tiene_prioridad_false(self):
        self.assertFalse(_j("A", prioridad="False").tiene_prioridad)

    def test_puntaje_nuevo_es_cero(self):
        # Un jugador nuevo siempre tiene la máxima prioridad (0)
        self.assertEqual(_j("A", experiencia="Nuevo", juegos_ano=10).puntaje_prioridad, 0)

    def test_puntaje_prioridad_flag_es_cero(self):
        # El flag de prioridad también produce puntaje 0
        self.assertEqual(_j("A", prioridad="True", juegos_ano=10).puntaje_prioridad, 0)

    def test_puntaje_antiguo_sin_juegos_este_ano(self):
        # Antiguo con 0 juegos: penalización mínima (0.05) para distinguirlo del nuevo.
        self.assertAlmostEqual(_j("A", juegos_ano=0).puntaje_prioridad, 0.05)

    def test_puntaje_antiguo_con_juegos(self):
        # 0.05 + 3 × 0.15 = 0.50
        self.assertAlmostEqual(_j("A", juegos_ano=3).puntaje_prioridad, 0.50)

    def test_puntaje_cap_en_noventa(self):
        # Con muchos juegos la fracción no puede superar 0.90
        self.assertAlmostEqual(_j("A", juegos_ano=10).puntaje_prioridad, 0.90)

    def test_jugador_sin_gm_no_es_reducido_como_gm(self):
        """Para un no-GM con partidas_deseadas=2 el algoritmo genera ambos tickets.

        Al dar a X el puntaje_prioridad más alto (juegos_ano=10 → weight 1.90),
        su primer ticket se procesa DESPUÉS de los 12 jugadores normales (1.05).
        Cuando llega el primer ticket de X los 12 cupos están repartidos [6,6];
        va a una mesa → [7,6]. Su segundo ticket (weight 2.90) solo puede ir a la
        otra mesa → [7,7]. X aparece siempre en exactamente 2 mesas distintas.
        """
        for seed in range(20):
            random.seed(seed)
            jugadores = _pool(12, juegos_ano=0) + [_j("X", juegos_ano=10, partidas_deseadas=2)]
            res = _calcular_partidas(jugadores)
            mesas_de_x = sum(1 for m in res.mesas if any(j.nombre == "X" for j in m.jugadores))
            self.assertEqual(mesas_de_x, 2, f"X no aparece en 2 mesas distintas (seed={seed})")

    def test_partidas_gm_se_almacena(self):
        self.assertEqual(_j("A", partidas_gm=2).partidas_gm, 2)


# ── Tests del algoritmo principal ─────────────────────────────────────────────

class TestCalcularPartidas(unittest.TestCase):

    def setUp(self) -> None:
        # Semilla fija para que los tests que no iteran seeds sean deterministas
        random.seed(0)

    # ── Casos base ────────────────────────────────────────────────────────────

    def test_sin_jugadores_retorna_none(self):
        self.assertIsNone(_calcular_partidas([]))

    def test_menos_de_siete_jugadores_retorna_none(self):
        self.assertIsNone(_calcular_partidas(_pool(6)))

    def test_exactamente_siete_forma_una_partida(self):
        res = _calcular_partidas(_pool(7))
        self.assertIsNotNone(res)
        self.assertIsInstance(res, ResultadoPartidas)
        self.assertEqual(len(res.mesas), 1)
        self.assertEqual(len(res.mesas[0].jugadores), 7)

    def test_catorce_jugadores_forman_dos_partidas(self):
        res = _calcular_partidas(_pool(14))
        self.assertIsNotNone(res)
        self.assertEqual(len(res.mesas), 2)

    def test_tickets_multiples_cuentan_correctamente(self):
        # 12 quieren 1 partida + 2 quieren 2 = 16 tickets → 2 mesas
        jugadores = _pool(12) + [
            _j("Multi1", partidas_deseadas=2),
            _j("Multi2", partidas_deseadas=2),
        ]
        res = _calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        self.assertEqual(len(res.mesas), 2)

    # ── Corrección de las mesas ───────────────────────────────────────────────

    def test_cada_mesa_tiene_exactamente_siete_jugadores(self):
        res = _calcular_partidas(_pool(14))
        self.assertIsNotNone(res)
        for mesa in res.mesas:
            self.assertEqual(len(mesa.jugadores), 7)

    def test_sin_duplicados_por_mesa(self):
        """Un jugador no puede aparecer dos veces en la misma mesa."""
        jugadores = _pool(10) + [_j("Multi", partidas_deseadas=2)]
        res = _calcular_partidas(jugadores)
        if res is None:
            return
        for mesa in res.mesas:
            nombres = [j.nombre for j in mesa.jugadores]
            self.assertEqual(len(nombres), len(set(nombres)), "Hay duplicados en una mesa")

    def test_jugador_multipartida_en_mesas_distintas(self):
        """Un jugador que quiere 2 partidas debe quedar en mesas diferentes."""
        jugadores = _pool(12) + [
            _j("Multi1", partidas_deseadas=2),
            _j("Multi2", partidas_deseadas=2),
        ]
        res = _calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        for nombre in ("Multi1", "Multi2"):
            mesas_del_jugador = [
                i for i, mesa in enumerate(res.mesas)
                if any(j.nombre == nombre for j in mesa.jugadores)
            ]
            self.assertEqual(len(set(mesas_del_jugador)), len(mesas_del_jugador),
                             f"{nombre} aparece en la misma mesa más de una vez")

    # ── Balance de experiencia ────────────────────────────────────────────────

    def test_balance_nuevos_y_antiguos_por_mesa(self):
        """Con una mezcla suficiente, cada mesa debe tener nuevos y antiguos."""
        jugadores = _pool(6, prefix="N", experiencia="Nuevo") + _pool(8, prefix="A")
        res = _calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        for mesa in res.mesas:
            self.assertTrue(any(j.es_nuevo for j in mesa.jugadores), "Mesa sin jugadores nuevos")
            self.assertTrue(any(not j.es_nuevo for j in mesa.jugadores), "Mesa sin jugadores antiguos")

    # ── Error de configuración ────────────────────────────────────────────────

    def test_error_mas_gm_slots_que_partidas(self):
        """Si hay más slots de GM que mesas, debe lanzar ValueError."""
        jugadores = _pool(7)  # 1 mesa
        jugadores += [_j("GM1", partidas_gm=1), _j("GM2", partidas_gm=1)]
        with self.assertRaises(ValueError):
            _calcular_partidas(jugadores)

    def test_un_gm_en_unica_mesa_no_es_error(self):
        """Un solo GM para una sola mesa es configuración válida."""
        jugadores = _pool(7) + [_j("GM1", partidas_gm=1)]
        res = _calcular_partidas(jugadores)  # no debe lanzar excepción
        self.assertIsNotNone(res)

    # ── Lista de espera ───────────────────────────────────────────────────────

    def test_lista_de_espera_contiene_jugadores_sobrantes(self):
        """Con 15 jugadores (2 mesas = 14 cupos), 1 debe quedar en espera."""
        res = _calcular_partidas(_pool(15))
        self.assertIsNotNone(res)
        self.assertEqual(len(res.mesas), 2)
        total_colocados = sum(len(m.jugadores) for m in res.mesas)
        total_sobrantes = len(res.tickets_sobrantes)
        self.assertEqual(total_colocados + total_sobrantes, 15)

    def test_todos_entran_cuando_hay_cupos_exactos(self):
        """Si los tickets caben exactamente, la lista de espera debe estar vacía."""
        res = _calcular_partidas(_pool(14))
        self.assertIsNotNone(res)
        self.assertEqual(len(res.tickets_sobrantes), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
