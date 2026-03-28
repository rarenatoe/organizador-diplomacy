from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Jugador, ResultadoPartidas

# ── Country Assignment Algorithm ───────────────────────────────────────────

def assign_countries_to_mesa(jugadores: list[Jugador]) -> None:
    """
    Assign countries to players using a "shielding" strategy.
    Only assigns countries to prevent players from repeating countries they've played 2+ times.
    """
    # Initialize all players with no country
    for player in jugadores:
        player.pais = ""
        player.pais_reason = None
    
    # Identify cursed players (those with >= 2 games in any country)
    cursed_assignments: list[tuple[Jugador, str, int]] = []
    for player in jugadores:
        country_counts = {
            "England": player.c_england,
            "France": player.c_france,
            "Germany": player.c_germany,
            "Italy": player.c_italy,
            "Austria": player.c_austria,
            "Russia": player.c_russia,
            "Turkey": player.c_turkey
        }
        
        for country, count in country_counts.items():
            if count >= 2:
                cursed_assignments.append((player, country, count))
    
    # For each cursed assignment, find a shield player
    for cursed_player, country, count in cursed_assignments:
        # Find the best shield player (no country assigned, lowest historical count for this country)
        best_shield_player: Jugador | None = None
        best_shield_count = float('inf')
        
        for potential_shield in jugadores:
            if potential_shield.pais == "" and potential_shield != cursed_player:
                shield_count = getattr(potential_shield, f"c_{country.lower()}", 0)
                if shield_count < best_shield_count:
                    best_shield_count = shield_count
                    best_shield_player = potential_shield
        
        # Assign the shield player
        if best_shield_player:
            best_shield_player.pais = country
            times = "veces" if count > 1 else "vez"
            best_shield_player.pais_reason = f"Asignación protectora: Se le asignó este país para evitar que {cursed_player.nombre} lo repita ({count} {times})."

# ── Algorithm Orchestrator ───────────────────────────────────────────────────

def calcular_partidas(jugadores: list[Jugador]) -> ResultadoPartidas | None:
    """
    Núcleo del algoritmo orquestado. Devuelve un ResultadoPartidas, 
    o None si no hay suficientes jugadores para armar una partida.
    Lanza ValueError si la configuración de GMs es inválida.
    """
    from .distribution import run_distribution_loop
    from .weights import build_weighted_tickets

    (
        mesas_estimadas,
        mesas_reales,
        minimo_teorico,
        gms_activos,
        weighted_tickets
    ) = build_weighted_tickets(jugadores)

    if mesas_reales == 0:
        return None

    # Assign countries to each mesa before running distribution
    for mesa in range(mesas_reales):
        mesa_players = [jugadores[i] for i in range(mesa * 7, (mesa + 1) * 7) if i < len(jugadores)]
        assign_countries_to_mesa(mesa_players)

    return run_distribution_loop(
        jugadores=jugadores,
        weighted_tickets=weighted_tickets,
        gms_activos=gms_activos,
        mesas_estimadas=mesas_estimadas,
        mesas_reales=mesas_reales,
        minimo_teorico=minimo_teorico,
        max_intentos=200
    )
