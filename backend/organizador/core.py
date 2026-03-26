from __future__ import annotations

from .models import Jugador, ResultadoPartidas
from .weights import build_weighted_tickets
from .distribution import run_distribution_loop

# ── Algorithm Orchestrator ───────────────────────────────────────────────────

def calcular_partidas(jugadores: list[Jugador]) -> ResultadoPartidas | None:
    """
    Núcleo del algoritmo orquestado. Devuelve un ResultadoPartidas, 
    o None si no hay suficientes jugadores para armar una partida.
    Lanza ValueError si la configuración de GMs es inválida.
    """
    (
        mesas_estimadas,
        mesas_reales,
        minimo_teorico,
        gms_activos,
        weighted_tickets
    ) = build_weighted_tickets(jugadores)

    if mesas_reales == 0:
        return None

    return run_distribution_loop(
        jugadores=jugadores,
        weighted_tickets=weighted_tickets,
        gms_activos=gms_activos,
        mesas_estimadas=mesas_estimadas,
        mesas_reales=mesas_reales,
        minimo_teorico=minimo_teorico,
        max_intentos=200
    )
