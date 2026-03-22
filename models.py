"""
models.py – Domain types shared across organizador.py, formatter.py, and viewer.py.

  Jugador           – a player with priority score logic
  Mesa              – a game table (7 players + optional GM)
  ResultadoPartidas – typed algorithm result
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── CSV column reference ───────────────────────────────────────────────────────
# Columns: Nombre, Experiencia, Juegos_Este_Ano, Prioridad, Partidas_Deseadas, Partidas_GM


class Jugador:
    def __init__(
        self,
        nombre: str,
        experiencia: str,
        juegos_ano: str | int,
        prioridad: str,
        partidas_deseadas: str | int,
        partidas_gm: str | int = 0,
    ) -> None:
        self.nombre: str = nombre
        self.es_nuevo: bool = (experiencia.strip().lower() == "nuevo")
        self.juegos_ano: int = int(juegos_ano)
        self.tiene_prioridad: bool = (prioridad.strip().lower() == "true")
        self.partidas_deseadas: int = int(partidas_deseadas)
        # How many tables this player will referee as GM (0 = not a GM).
        # The algorithm assigns which specific table(s) automatically.
        self.partidas_gm: int = int(partidas_gm)

    @property
    def puntaje_prioridad(self) -> float:
        """
        Continuous priority fraction used in weight_after. Lower = higher priority.

        Scale:
          0.00  → nuevo or has priority flag
          0.05  → antiguo, 0 games this year
          0.20  → antiguo, 1 game this year
          0.35  → antiguo, 2 games this year
          0.50  → antiguo, 3 games this year
           ⋮    0.05 + juegos_ano × 0.15, max 0.90

        The 0.15 step per game (vs 0.10 previously) equilibrates the league
        faster: someone with 4 games (0.65) clearly yields to someone with 0 (0.05).
        """
        if self.es_nuevo or self.tiene_prioridad:
            return 0.0
        return min(0.05 + self.juegos_ano * 0.15, 0.90)


@dataclass
class Mesa:
    """A game table with its players and optional Game Master."""
    numero: int                        # 1-based, for display
    jugadores: list[Jugador]
    gm: Jugador | None = None


@dataclass
class ResultadoPartidas:
    """Typed algorithm result. Attribute access instead of dict keys."""
    mesas: list[Mesa]
    tickets_sobrantes: list[Jugador]
    minimo_teorico: int = 0    # tickets that cannot fit in any scenario
    intentos_usados: int = 0   # retry-loop iterations consumed
