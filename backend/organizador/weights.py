from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Jugador

# ── Weighted Tickets Setup ───────────────────────────────────────────────────

def build_weighted_tickets(jugadores: list[Jugador]) -> tuple[int, int, int, list[Jugador], list[tuple[float, Jugador]]]:
    """
    Calculates the estimated and real tables, theoretical minimum waitlist,
    active GMs, and weighted tickets list based on player priority and GM roles.

    Returns:
        tuple: (mesas_estimadas, mesas_reales, minimo_teorico, gms_activos, weighted_tickets)
    """
    total_tickets_brutos: int = sum(j.partidas_deseadas for j in jugadores)
    mesas_estimadas: int = total_tickets_brutos // 7

    if mesas_estimadas == 0:
        return 0, 0, 0, [], []

    # Cada mesa acepta exactamente un GM.
    total_slots_gm: int = sum(j.partidas_gm for j in jugadores)
    if total_slots_gm > mesas_estimadas:
        raise ValueError(
            f"Hay {total_slots_gm} slot(s) de GM pero solo {mesas_estimadas} "
            f"partida(s). Cada mesa acepta un único GM."
        )

    # Cupos reales de juego: GMs descontados, sin mutar los objetos Jugador.
    jugables: dict[str, int] = {
        jugador.nombre: (
            min(jugador.partidas_deseadas, mesas_estimadas - jugador.partidas_gm)
            if jugador.partidas_gm > 0
            else jugador.partidas_deseadas
        )
        for jugador in jugadores
    }

    # GMs ordenados: los que arbitran más mesas reciben su asignación primero.
    gms_activos: list[Jugador] = sorted(
        [j for j in jugadores if j.partidas_gm > 0],
        key=lambda j: j.partidas_gm,
        reverse=True,
    )

    # Tickets con peso de participación (pesos determinísticos).
    #
    #   weight_after = gm_weight + slot_index + jugador.puntaje_prioridad
    #
    #   gm_weight         = partidas_gm × 0.5
    #   slot_index        = 1.0 para 1er cupo, 2.0 para 2do, etc.
    #   puntaje_prioridad = fracción continua [0.00, 0.90]
    #
    # Invariantes:
    #   • Primeros slots [1.00, 1.90] < segundos slots [2.00, 2.90] →
    #     nadie queda con 0 participaciones mientras hay cupo.
    #   • Dentro del mismo slot, menos juegos → menor peso → entra antes.
    weighted_tickets: list[tuple[float, Jugador]] = []
    for jugador in jugadores:
        gm_weight: float = jugador.partidas_gm * 0.5
        priority_fraction: float = jugador.puntaje_prioridad
        for i in range(jugables[jugador.nombre]):
            weight_after: float = gm_weight + float(i + 1) + priority_fraction
            weighted_tickets.append((weight_after, jugador))

    mesas_reales: int = len(weighted_tickets) // 7

    if mesas_reales == 0:
        return mesas_estimadas, 0, 0, gms_activos, []

    # Piso de la lista de espera: tickets que no caben en ningún escenario.
    minimo_teorico: int = len(weighted_tickets) - mesas_reales * 7

    return mesas_estimadas, mesas_reales, minimo_teorico, gms_activos, weighted_tickets
