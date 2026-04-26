"""Pydantic models for the Games API."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from pydantic import BaseModel

from backend.organizador.models import DraftPlayer, DraftResult  # noqa: TC001


class CountrySelection(BaseModel):
    name: str
    reason: list[str] = []


class GameDraftPlayer(BaseModel):
    nombre: str
    is_new: bool
    juegos_este_ano: int
    has_priority: bool
    partidas_deseadas: int
    partidas_gm: int
    c_england: int
    c_france: int
    c_germany: int
    c_italy: int
    c_austria: int
    c_russia: int
    c_turkey: int
    country: CountrySelection
    cupos_faltantes: int | None = None

    @classmethod
    def from_domain(cls, p: DraftPlayer, waitlist_count: int | None = None) -> GameDraftPlayer:
        return cls(
            nombre=p.name,
            is_new=p.is_new,
            juegos_este_ano=p.games_this_year,
            has_priority=p.has_priority,
            partidas_deseadas=p.desired_games,
            partidas_gm=p.gm_games,
            c_england=p.c_england,
            c_france=p.c_france,
            c_germany=p.c_germany,
            c_italy=p.c_italy,
            c_austria=p.c_austria,
            c_russia=p.c_russia,
            c_turkey=p.c_turkey,
            country=CountrySelection(name=p.country, reason=p.country_reason),
            cupos_faltantes=waitlist_count,
        )


class GameDraftTable(BaseModel):
    numero: int
    gm: GameDraftPlayer | None = None
    jugadores: list[GameDraftPlayer]


class GameDraftResponse(BaseModel):
    mesas: list[GameDraftTable]
    tickets_sobrantes: list[GameDraftPlayer]
    minimo_teorico: int
    intentos_usados: int

    @classmethod
    def from_domain(cls, resultado: DraftResult) -> GameDraftResponse:
        waitlist_counts = Counter(p.name for p in resultado.waitlist_players)
        unique_waitlist = list({p.name: p for p in resultado.waitlist_players}.values())

        mesas = [
            GameDraftTable(
                numero=table.table_number,
                gm=GameDraftPlayer.from_domain(table.gm) if table.gm else None,
                jugadores=[GameDraftPlayer.from_domain(p) for p in table.players],
            )
            for table in resultado.tables
        ]

        tickets_sobrantes = [
            GameDraftPlayer.from_domain(p, waitlist_counts[p.name]) for p in unique_waitlist
        ]

        return cls(
            mesas=mesas,
            tickets_sobrantes=tickets_sobrantes,
            minimo_teorico=resultado.theoretical_minimum,
            intentos_usados=resultado.attempts_used,
        )


class GameDetailResponse(BaseModel):
    id: int
    created_at: datetime | str
    intentos: int
    mesas: list[GameDraftTable]
    waiting_list: list[GameDraftPlayer]
    input_snapshot_id: int | None = None
    output_snapshot_id: int | None = None


class GameDraftRequest(BaseModel):
    snapshot_id: int


class GameSaveRequest(BaseModel):
    snapshot_id: int
    draft: GameDraftResponse
    editing_game_id: int | None = None
