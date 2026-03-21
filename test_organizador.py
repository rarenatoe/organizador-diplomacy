"""
Tests de unidad para organizador.py

Cubre:
  - Clase Jugador (atributos y puntaje de prioridad)
  - _calcular_partidas: número de mesas, balance, duplicados, prioridad,
    reglas de GM, lista de espera y casos de error.
"""
import random
import unittest

from organizador import Jugador, ResultadoPartidas, _calcular_partidas


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

    # ── Prioridad de selección ────────────────────────────────────────────────

    def test_jugador_nuevo_siempre_entra_sobre_veterano(self):
        """Con 1 cupo extra, el jugador nuevo entra antes que el veterano con más juegos."""
        for seed in range(30):
            random.seed(seed)
            jugadores = (
                [_j(f"Vet{i}", juegos_ano=5) for i in range(13)]
                + [_j("Nuevo1", experiencia="Nuevo")]
                + [_j("Extra", juegos_ano=5)]
            )
            res = _calcular_partidas(jugadores)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            self.assertIn("Nuevo1", todos, f"Nuevo1 no entró (seed={seed})")

    def test_jugador_con_prioridad_siempre_entra_sobre_veterano(self):
        """Con 1 cupo extra, el jugador con prioridad entra antes que el veterano."""
        for seed in range(30):
            random.seed(seed)
            jugadores = (
                [_j(f"Vet{i}", juegos_ano=5) for i in range(13)]
                + [_j("Prior", prioridad="True", juegos_ano=5)]
                + [_j("Extra", juegos_ano=5)]
            )
            res = _calcular_partidas(jugadores)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            self.assertIn("Prior", todos, f"Prior no entró (seed={seed})")

    def test_antiguo_sin_juegos_este_ano_entra_antes_que_veterano(self):
        """Antiguo con 0 juegos este año (puntaje 1) entra antes que veterano (puntaje 7+)."""
        for seed in range(30):
            random.seed(seed)
            jugadores = (
                [_j(f"Vet{i}", juegos_ano=5) for i in range(13)]
                + [_j("SinJuegos", juegos_ano=0)]
                + [_j("Extra", juegos_ano=5)]
            )
            res = _calcular_partidas(jugadores)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            self.assertIn("SinJuegos", todos, f"SinJuegos no entró (seed={seed})")

    # ── Reglas de Game Master ─────────────────────────────────────────────────

    def test_gm_no_juega_en_su_mesa(self):
        """Un GM nunca debe aparecer como jugador en la mesa que arbitra."""
        for seed in range(30):
            random.seed(seed)
            jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
            res = _calcular_partidas(jugadores)
            if res is None:
                continue
            for mesa in res.mesas:
                if mesa.gm and mesa.gm.nombre == "GM1":
                    self.assertNotIn("GM1", [j.nombre for j in mesa.jugadores],
                                     f"GM1 juega en su propia mesa (seed={seed})")

    def test_gm_puede_jugar_en_mesa_que_no_arbitra(self):
        """Un GM puede aparecer como jugador en una mesa distinta a la que arbitra."""
        jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
        res = _calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
        self.assertIn("GM1", todos, "GM1 debería poder jugar en la mesa que no arbitra")

    def test_gm_aparece_como_arbitro_en_alguna_mesa(self):
        """El GM asignado aparece como árbitro en al menos una mesa."""
        jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
        res = _calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        self.assertTrue(any(m.gm and m.gm.nombre == "GM1" for m in res.mesas),
                        "GM1 no aparece como árbitro en ninguna mesa")

    def test_solo_un_gm_por_mesa(self):
        """Cada mesa tiene como máximo un GM árbitro."""
        jugadores = _pool(12) + [
            _j("GM1", partidas_gm=1),
            _j("GM2", partidas_gm=1),
        ]
        res = _calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        for mesa in res.mesas:
            self.assertIsInstance(mesa.gm, (Jugador, type(None)))

    def test_dos_gms_en_mesas_distintas(self):
        """Dos GMs nunca deben ser asignados a arbitrar la misma mesa."""
        for seed in range(30):
            random.seed(seed)
            jugadores = _pool(12) + [
                _j("GM1", partidas_deseadas=2, partidas_gm=1),
                _j("GM2", partidas_deseadas=2, partidas_gm=1),
            ]
            res = _calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            mesas_gm1 = {i for i, m in enumerate(res.mesas) if m.gm and m.gm.nombre == "GM1"}
            mesas_gm2 = {i for i, m in enumerate(res.mesas) if m.gm and m.gm.nombre == "GM2"}
            self.assertEqual(
                len(mesas_gm1 & mesas_gm2), 0,
                f"GM1 y GM2 comparten mesa como árbitros (seed={seed})"
            )

    def test_gm_reduce_partidas_jugables_correctamente(self):
        """El GM solo juega en mesas que no arbitra: máx min(deseadas, total_mesas - arbitradas)."""
        # 13 jugadores + GM1 (desea 2, arbitra 1) → 2 mesas; GM1 puede jugar en como máx 1.
        jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
        for seed in range(20):
            random.seed(seed)
            res = _calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            mesas_jugadas = sum(1 for mesa in res.mesas for j in mesa.jugadores if j.nombre == "GM1")
            mesas_arbitradas = sum(1 for m in res.mesas if m.gm and m.gm.nombre == "GM1")
            self.assertLessEqual(mesas_jugadas, len(res.mesas) - mesas_arbitradas)

    # ── GM cede su cupo de jugador ────────────────────────────────────────────

    def test_gm_menor_prioridad_como_jugador_que_jugador_puro(self):
        """Con exactamente 1 cupo sobrante, el jugador puro entra y el GM cede su plaza."""
        for seed in range(30):
            random.seed(seed)
            jugadores = _pool(14) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
            res = _calcular_partidas(jugadores)
            self.assertIsNotNone(res)

            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            sobrantes = {j.nombre for j in res.tickets_sobrantes}

            for i in range(14):
                self.assertIn(f"J{i}", todos, f"J{i} no entró (seed={seed})")

            self.assertNotIn("GM1", todos, f"GM1 ocupó un cupo de jugador (seed={seed})")
            self.assertIn("GM1", sobrantes, f"GM1 no está en lista de espera (seed={seed})")

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

    # ── Balanceo de liga (juegos_ano) ──────────────────────────────────────────

    def test_veterano_cede_primer_slot_cuando_hay_escasez(self):
        """Con más candidatos que cupos, el jugador con más juegos_ano queda fuera.

        Con la escala 0.05 + N×0.15:
          - jugador 0 juegos → weight 1.05
          - Veterano 8 juegos → weight 1.90 (cap 0.90)
        El gap de 0.85 garantiza que el veterano siempre es el sobrante.
        """
        for seed in range(40):
            random.seed(seed)
            jugadores = _pool(14, juegos_ano=0) + [_j("Veterano", juegos_ano=8)]
            res = _calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            sobrantes = {j.nombre for j in res.tickets_sobrantes}
            for i in range(14):
                self.assertIn(f"J{i}", todos, f"J{i} no entró (seed={seed})")
            self.assertNotIn("Veterano", todos,
                             f"Veterano ocupó un cupo que debía ser de otro (seed={seed})")
            self.assertIn("Veterano", sobrantes, f"Veterano no está en espera (seed={seed})")

    def test_todos_obtienen_primer_cupo_antes_de_segundos_cupos_con_historial(self):
        """Reproducción del caso Jean Carlos.

        Con 16 tickets para 14 cupos, donde Jean Carlos tiene más juegos_ano
        que los demás, su SEGUNDO cupo debe ser el sobrante, no su primero.
        Todos los jugadores deben tener al menos una participación.
        """
        for seed in range(40):
            random.seed(seed)
            # 12 con 0 juegos + DanielV (0 juegos, quiere 2) + JeanCarlos (3 juegos, quiere 2)
            # Tickets: 12×1 + 2×2 = 16 → 14 aceptados, 2 sobrantes.
            # Sobrantes esperados: los dos SEGUNDOS tickets (weight ≥2.0),
            # no el primer ticket de JeanCarlos (weight 1.4).
            jugadores = _pool(12, juegos_ano=0) + [
                _j("DanielV",   juegos_ano=0, partidas_deseadas=2),
                _j("JeanCarlos", juegos_ano=3, partidas_deseadas=2),
            ]
            res = _calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            # TODOS los jugadores deben aparecer en al menos una mesa
            for j in jugadores:
                self.assertIn(
                    j.nombre, todos,
                    f"{j.nombre} quedó con 0 cupos (seed={seed})",
                )

    # ── Peso de participación (0.5 GM / 1.0 jugador) ──────────────────────────

    def test_primer_cupo_siempre_antes_que_segundo_cupo(self):
        """Ningún jugador se queda con 0 cupos mientras otro tiene 2+.

        Reproduce el bug reportado: Jean Carlos quería 2 partidas pero quedaba
        fuera mientras Charlie y Daniel Villafranca jugaban doble.
        Con la lógica de weight_after, todos los primeros tickets (weight 1.0)
        se asignan antes que cualquier segundo ticket (weight 2.0).
        """
        for seed in range(50):
            random.seed(seed)
            # 2 mesas (14 cupos). 8 jugadores de 1 cupo + 4 quieren 2 cupos.
            # Total tickets: 8×1 + 4×2 = 16 → 14 aceptados, 2 sobrantes.
            # Los 2 sobrantes deben ser segundos tickets; todos deben tener ≥1 cupo.
            jugadores = _pool(8) + [
                _j("I", partidas_deseadas=2),
                _j("J", partidas_deseadas=2),
                _j("K", partidas_deseadas=2),
                _j("JeanCarlos", partidas_deseadas=2),
            ]
            res = _calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            for j in jugadores:
                self.assertIn(
                    j.nombre, todos,
                    f"{j.nombre} quedó con 0 cupos (seed={seed})",
                )

    def test_gm_preferido_sobre_segundo_cupo_de_jugador_puro(self):
        """Un GM buscando su 1er cupo de jugador (weight 1.5) tiene preferencia
        sobre un jugador puro buscando su 2do cupo (weight 2.0).

        Escenario: 2 mesas, 12 jugadores puros de 1 cupo + 1 jugador que quiere
        2 cupos + 1 GM que quiere 2 pero arbitra 1 (→ 1 jugable).
        Total tickets: 12 + 2 + 1 = 15. Se aceptan 14.
        El sobrante siempre debe ser el 2do ticket del jugador puro (weight 2.0),
        nunca el del GM (weight 1.5).
        """
        for seed in range(50):
            random.seed(seed)
            jugadores = _pool(12) + [
                _j("Multi", partidas_deseadas=2),                 # weights 1.0, 2.0
                _j("GM1", partidas_deseadas=2, partidas_gm=1),   # weight 1.5 como jugador
            ]
            res = _calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            sobrantes = {j.nombre for j in res.tickets_sobrantes}

            # GM1 SIEMPRE debe obtener su cupo de jugador (weight 1.5 < 2.0)
            self.assertIn("GM1", todos,
                          f"GM1 no obtuvo cupo de jugador (seed={seed})")
            # Multi también debe obtener al menos su 1er cupo
            self.assertIn("Multi", todos,
                          f"Multi quedó con 0 cupos (seed={seed})")
            # El sobrante debe ser el 2do ticket de Multi, no el de GM1
            self.assertNotIn("GM1", sobrantes,
                             f"GM1 está en lista de espera en lugar de Multi (seed={seed})")


if __name__ == "__main__":
    unittest.main(verbosity=2)
