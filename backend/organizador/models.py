"""
models.py – Domain types shared across organizador.py, formatter.py, and viewer.py.

  DraftPlayer      – a player with priority score logic (Pydantic model)
  DraftTable       – a game table (7 players + optional GM) (Pydantic model)
  DraftResult      – typed algorithm result (Pydantic model)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator

# ── CSV column reference ───────────────────────────────────────────────────────
# Columns: Nombre, is_new, Juegos_Este_Ano, Prioridad, Partidas_Deseadas, Partidas_GM


class DraftPlayer(BaseModel):
    """A player with priority score logic."""

    name: str
    is_new: bool = False
    games_this_year: int
    has_priority: bool = False
    desired_games: int
    gm_games: int = 0
    c_england: int = 0
    c_france: int = 0
    c_germany: int = 0
    c_italy: int = 0
    c_austria: int = 0
    c_russia: int = 0
    c_turkey: int = 0
    country: str = ""
    country_reason: str | None = None

    @field_validator("games_this_year", "desired_games", "gm_games", mode="before")
    @classmethod
    def coerce_to_int(_cls, v: Any) -> int:
        """Coerce string or int values to int."""
        return int(v)

    @property
    def priority_score(self) -> float:
        """
        Continuous priority fraction used in weight_after. Lower = higher priority.

        Scale:
          0.00  → nuevo or has priority flag
          0.05  → antiguo, 0 games this year
          0.20  → antiguo, 1 game this year
          0.35  → antiguo, 2 games this year
          0.50  → antiguo, 3 games this year
           ⋮    0.05 + games_this_year × 0.15, max 0.90

        The 0.15 step per game (vs 0.10 previously) equilibrates the league
        faster: someone with 4 games (0.65) clearly yields to someone with 0 (0.05).
        """
        if self.is_new or self.has_priority:
            return 0.0
        return min(0.05 + int(self.games_this_year) * 0.15, 0.90)


class DraftTable(BaseModel):
    """A game table with its players and optional Game Master."""

    table_number: int  # 1-based, for display
    players: list[DraftPlayer]
    gm: DraftPlayer | None = None


class DraftResult(BaseModel):
    """Typed algorithm result. Attribute access instead of dict keys."""

    tables: list[DraftTable]
    waitlist_players: list[DraftPlayer]
    theoretical_minimum: int = 0  # tickets that cannot fit in any scenario
    attempts_used: int = 0  # retry-loop iterations consumed
