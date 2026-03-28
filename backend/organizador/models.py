"""
models.py – Domain types shared across organizador.py, formatter.py, and viewer.py.

  Jugador           – a player with priority score logic
  Mesa              – a game table (7 players + optional GM)
  ResultadoPartidas – typed algorithm result
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
        c_england: int = 0,
        c_france: int = 0,
        c_germany: int = 0,
        c_italy: int = 0,
        c_austria: int = 0,
        c_russia: int = 0,
        c_turkey: int = 0,
        pais: str = "",
        pais_reason: str | None = None,
    ) -> None:
        self.nombre: str = nombre
        self.es_nuevo: bool = (experiencia.strip().lower() == "nuevo")
        self.juegos_ano: int = int(juegos_ano)
        self.tiene_prioridad: bool = str(prioridad).strip().lower() in ("true", "1")
        self.partidas_deseadas: int = int(partidas_deseadas)
        # How many tables this player will referee as GM (0 = not a GM).
        # The algorithm assigns which specific table(s) automatically.
        self.partidas_gm: int = int(partidas_gm)
        
        # Country history counts
        self.c_england: int = int(c_england)
        self.c_france: int = int(c_france)
        self.c_germany: int = int(c_germany)
        self.c_italy: int = int(c_italy)
        self.c_austria: int = int(c_austria)
        self.c_russia: int = int(c_russia)
        self.c_turkey: int = int(c_turkey)
        self.pais: str = pais
        self.pais_reason: str | None = pais_reason

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "nombre": self.nombre,
            "es_nuevo": self.es_nuevo,
            "juegos_ano": self.juegos_ano,
            "tiene_prioridad": self.tiene_prioridad,
            "partidas_deseadas": self.partidas_deseadas,
            "partidas_gm": self.partidas_gm,
            "c_england": self.c_england,
            "c_france": self.c_france,
            "c_germany": self.c_germany,
            "c_italy": self.c_italy,
            "c_austria": self.c_austria,
            "c_russia": self.c_russia,
            "c_turkey": self.c_turkey,
            "pais": self.pais,
        }
        if self.pais_reason is not None:
            d["pais_reason"] = self.pais_reason
        return d

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "numero": self.numero,
            "jugadores": [j.to_dict() for j in self.jugadores],
            "gm": self.gm.to_dict() if self.gm else None,
        }


@dataclass
class ResultadoPartidas:
    """Typed algorithm result. Attribute access instead of dict keys."""
    mesas: list[Mesa]
    tickets_sobrantes: list[Jugador]
    minimo_teorico: int = 0    # tickets that cannot fit in any scenario
    intentos_usados: int = 0   # retry-loop iterations consumed

    def to_dict(self) -> dict[str, Any]:
        return {
            "mesas": [m.to_dict() for m in self.mesas],
            "tickets_sobrantes": [j.to_dict() for j in self.tickets_sobrantes],
            "minimo_teorico": self.minimo_teorico,
            "intentos_usados": self.intentos_usados
        }
