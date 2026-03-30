"""
models.py – Domain types shared across organizador.py, formatter.py, and viewer.py.

  Jugador           – a player with priority score logic (Pydantic model)
  Mesa              – a game table (7 players + optional GM) (Pydantic model)
  ResultadoPartidas – typed algorithm result (Pydantic model)
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ── CSV column reference ───────────────────────────────────────────────────────
# Columns: Nombre, Experiencia, Juegos_Este_Ano, Prioridad, Partidas_Deseadas, Partidas_GM


class Jugador(BaseModel):
    """A player with priority score logic."""

    nombre: str
    experiencia: str
    juegos_ano: str | int
    prioridad: str
    partidas_deseadas: str | int
    partidas_gm: str | int = 0
    c_england: int = 0
    c_france: int = 0
    c_germany: int = 0
    c_italy: int = 0
    c_austria: int = 0
    c_russia: int = 0
    c_turkey: int = 0
    pais: str = ""
    pais_reason: str | None = None

    # Computed fields (set during initialization)
    es_nuevo: bool = Field(default=False)
    tiene_prioridad: bool = Field(default=False)

    def model_post_init(self, __context: Any) -> None:  # noqa: ARG002  # vulture: ignore
        """Parse string inputs and compute derived fields after initialization."""
        # Parse string inputs to proper types
        object.__setattr__(self, "es_nuevo", self.experiencia.strip().lower() == "nuevo")
        object.__setattr__(
            self, "tiene_prioridad", str(self.prioridad).strip().lower() in ("true", "1")
        )
        # Ensure integer fields are properly typed
        object.__setattr__(self, "juegos_ano", int(self.juegos_ano))
        object.__setattr__(self, "partidas_deseadas", int(self.partidas_deseadas))
        object.__setattr__(self, "partidas_gm", int(self.partidas_gm))

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
        return min(0.05 + int(self.juegos_ano) * 0.15, 0.90)


class Mesa(BaseModel):
    """A game table with its players and optional Game Master."""

    numero: int  # 1-based, for display
    jugadores: list[Jugador]
    gm: Jugador | None = None


class ResultadoPartidas(BaseModel):
    """Typed algorithm result. Attribute access instead of dict keys."""

    mesas: list[Mesa]
    tickets_sobrantes: list[Jugador]
    minimo_teorico: int = 0  # tickets that cannot fit in any scenario
    intentos_usados: int = 0  # retry-loop iterations consumed
