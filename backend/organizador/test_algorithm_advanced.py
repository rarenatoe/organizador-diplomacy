"""
Tests avanzados del algoritmo de organizar_partidas.

Cubre reglas complejas de ordenación y prioridad:
  - Prioridad de selección (Nuevo > prioridad > antiguo sin juegos > veterano)
  - Reglas de Game Master (no juega en su mesa, árbitro único, reduce cupos)
  - GM cede su cupo de jugador ante jugadores puros
  - Balanceo de liga (juegos_ano)
  - Peso de participación (primeros cupos antes que segundos)

Los tests básicos de corrección viven en test_organizador.py.
"""
import random
import unittest

from .core import calcular_partidas
from .models import Jugador

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


# ── Prioridad de selección ────────────────────────────────────────────────────

class TestCalcularPartidasPrioridad(unittest.TestCase):

    def setUp(self) -> None:
        random.seed(0)

    def test_jugador_nuevo_siempre_entra_sobre_veterano(self):
        """Con 1 cupo extra, el jugador nuevo entra antes que el veterano con más juegos."""
        for seed in range(30):
            random.seed(seed)
            jugadores = (
                [_j(f"Vet{i}", juegos_ano=5) for i in range(13)]
                + [_j("Nuevo1", experiencia="Nuevo")]
                + [_j("Extra", juegos_ano=5)]
            )
            res = calcular_partidas(jugadores)
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
            res = calcular_partidas(jugadores)
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
            res = calcular_partidas(jugadores)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            self.assertIn("SinJuegos", todos, f"SinJuegos no entró (seed={seed})")


# ── Reglas de Game Master ─────────────────────────────────────────────────────

class TestCalcularPartidasGM(unittest.TestCase):

    def setUp(self) -> None:
        random.seed(0)

    def test_gm_no_juega_en_su_mesa(self):
        """Un GM nunca debe aparecer como jugador en la mesa que arbitra."""
        for seed in range(30):
            random.seed(seed)
            jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
            res = calcular_partidas(jugadores)
            if res is None:
                continue
            for mesa in res.mesas:
                if mesa.gm and mesa.gm.nombre == "GM1":
                    self.assertNotIn("GM1", [j.nombre for j in mesa.jugadores],
                                     f"GM1 juega en su propia mesa (seed={seed})")

    def test_gm_puede_jugar_en_mesa_que_no_arbitra(self):
        """Un GM puede aparecer como jugador en una mesa distinta a la que arbitra."""
        jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
        res = calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
        self.assertIn("GM1", todos, "GM1 debería poder jugar en la mesa que no arbitra")

    def test_gm_aparece_como_arbitro_en_alguna_mesa(self):
        """El GM asignado aparece como árbitro en al menos una mesa."""
        jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
        res = calcular_partidas(jugadores)
        self.assertIsNotNone(res)
        self.assertTrue(any(m.gm and m.gm.nombre == "GM1" for m in res.mesas),
                        "GM1 no aparece como árbitro en ninguna mesa")

    def test_solo_un_gm_por_mesa(self):
        """Cada mesa tiene como máximo un GM árbitro."""
        jugadores = _pool(12) + [
            _j("GM1", partidas_gm=1),
            _j("GM2", partidas_gm=1),
        ]
        res = calcular_partidas(jugadores)
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
            res = calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            mesas_gm1 = {i for i, m in enumerate(res.mesas) if m.gm and m.gm.nombre == "GM1"}
            mesas_gm2 = {i for i, m in enumerate(res.mesas) if m.gm and m.gm.nombre == "GM2"}
            self.assertEqual(
                len(mesas_gm1 & mesas_gm2), 0,
                f"GM1 y GM2 comparten mesa como árbitros (seed={seed})"
            )

    def test_gm_reduce_partidas_jugables_correctamente(self):
        """El GM solo juega en mesas que no arbitra: máx min(deseadas, total_mesas - arbitradas)."""
        jugadores = _pool(13) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
        for seed in range(20):
            random.seed(seed)
            res = calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            mesas_jugadas = sum(1 for mesa in res.mesas for j in mesa.jugadores if j.nombre == "GM1")
            mesas_arbitradas = sum(1 for m in res.mesas if m.gm and m.gm.nombre == "GM1")
            self.assertLessEqual(mesas_jugadas, len(res.mesas) - mesas_arbitradas)

    def test_gm_menor_prioridad_como_jugador_que_jugador_puro(self):
        """Con exactamente 1 cupo sobrante, el jugador puro entra y el GM cede su plaza."""
        for seed in range(30):
            random.seed(seed)
            jugadores = _pool(14) + [_j("GM1", partidas_deseadas=2, partidas_gm=1)]
            res = calcular_partidas(jugadores)
            self.assertIsNotNone(res)

            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            sobrantes = {j.nombre for j in res.tickets_sobrantes}

            for i in range(14):
                self.assertIn(f"J{i}", todos, f"J{i} no entró (seed={seed})")

            self.assertNotIn("GM1", todos, f"GM1 ocupó un cupo de jugador (seed={seed})")
            self.assertIn("GM1", sobrantes, f"GM1 no está en lista de espera (seed={seed})")

    def test_gm_preferido_sobre_segundo_cupo_de_jugador_puro(self):
        """Un GM buscando su 1er cupo (weight 1.5) tiene preferencia sobre
        un jugador puro buscando su 2do cupo (weight 2.0)."""
        for seed in range(50):
            random.seed(seed)
            jugadores = _pool(12) + [
                _j("Multi", partidas_deseadas=2),                 # weights 1.0, 2.0
                _j("GM1", partidas_deseadas=2, partidas_gm=1),   # weight 1.5 como jugador
            ]
            res = calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            sobrantes = {j.nombre for j in res.tickets_sobrantes}

            self.assertIn("GM1", todos,
                          f"GM1 no obtuvo cupo de jugador (seed={seed})")
            self.assertIn("Multi", todos,
                          f"Multi quedó con 0 cupos (seed={seed})")
            self.assertNotIn("GM1", sobrantes,
                             f"GM1 está en lista de espera en lugar de Multi (seed={seed})")

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
            res = calcular_partidas(jugadores)
            mesas_de_x = sum(1 for m in res.mesas if any(j.nombre == "X" for j in m.jugadores))
            self.assertEqual(mesas_de_x, 2, f"X no aparece en 2 mesas distintas (seed={seed})")


# ── Balanceo de liga y peso de participación ──────────────────────────────────

class TestCalcularPartidasBalance(unittest.TestCase):

    def setUp(self) -> None:
        random.seed(0)

    def test_veterano_cede_primer_slot_cuando_hay_escasez(self):
        """Con más candidatos que cupos, el jugador con más juegos_ano queda fuera."""
        for seed in range(40):
            random.seed(seed)
            jugadores = _pool(14, juegos_ano=0) + [_j("Veterano", juegos_ano=8)]
            res = calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            sobrantes = {j.nombre for j in res.tickets_sobrantes}
            for i in range(14):
                self.assertIn(f"J{i}", todos, f"J{i} no entró (seed={seed})")
            self.assertNotIn("Veterano", todos,
                             f"Veterano ocupó un cupo que debía ser de otro (seed={seed})")
            self.assertIn("Veterano", sobrantes, f"Veterano no está en espera (seed={seed})")

    def test_todos_obtienen_primer_cupo_antes_de_segundos_cupos_con_historial(self):
        """Reproducción del caso Jean Carlos: el segundo ticket de quien tiene
        más juegos_ano es el sobrante, no su primer ticket."""
        for seed in range(40):
            random.seed(seed)
            jugadores = _pool(12, juegos_ano=0) + [
                _j("DanielV",    juegos_ano=0, partidas_deseadas=2),
                _j("JeanCarlos", juegos_ano=3, partidas_deseadas=2),
            ]
            res = calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            for j in jugadores:
                self.assertIn(
                    j.nombre, todos,
                    f"{j.nombre} quedó con 0 cupos (seed={seed})",
                )

    def test_primer_cupo_siempre_antes_que_segundo_cupo(self):
        """Ningún jugador se queda con 0 cupos mientras otro tiene 2+.

        Reproduce el bug: Jean Carlos quería 2 partidas pero quedaba fuera
        mientras otros jugaban doble.
        """
        for seed in range(50):
            random.seed(seed)
            jugadores = _pool(8) + [
                _j("I", partidas_deseadas=2),
                _j("J", partidas_deseadas=2),
                _j("K", partidas_deseadas=2),
                _j("JeanCarlos", partidas_deseadas=2),
            ]
            res = calcular_partidas(jugadores)
            self.assertIsNotNone(res)
            todos = {j.nombre for mesa in res.mesas for j in mesa.jugadores}
            for j in jugadores:
                self.assertIn(
                    j.nombre, todos,
                    f"{j.nombre} quedó con 0 cupos (seed={seed})",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
