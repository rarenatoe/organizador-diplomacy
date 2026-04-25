from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import DraftPlayer, DraftResult

# ── Country Assignment Algorithm ───────────────────────────────────────────


def assign_countries_to_table(players: list[DraftPlayer]) -> None:
    """
    Assign countries to players using a "shielding" strategy.
    Only assigns countries to prevent players from repeating countries they've played 2+ times.
    """
    # Initialize all players with no country
    for player in players:
        player.country = ""
        player.country_reason = ""

    # Identify cursed players (those with >= 2 games in any country)
    cursed_assignments: list[tuple[DraftPlayer, str, int]] = []
    for player in players:
        country_counts = {
            "England": player.c_england,
            "France": player.c_france,
            "Germany": player.c_germany,
            "Italy": player.c_italy,
            "Austria": player.c_austria,
            "Russia": player.c_russia,
            "Turkey": player.c_turkey,
        }

        for country, count in country_counts.items():
            if count >= 2:
                cursed_assignments.append((player, country, count))

    # For each cursed assignment, find a shield player
    for cursed_player, country, count in cursed_assignments:
        # Find the best shield player (no country assigned, lowest historical count for this country)
        best_shield_player: DraftPlayer | None = None
        best_shield_count = float("inf")

        for potential_shield in players:
            if potential_shield.country == "" and potential_shield != cursed_player:
                shield_count = getattr(potential_shield, f"c_{country.lower()}", 0)
                if shield_count < best_shield_count:
                    best_shield_count = shield_count
                    best_shield_player = potential_shield

        # Assign the shield player
        if best_shield_player:
            best_shield_player.country = country
            times = "veces" if count > 1 else "vez"
            best_shield_player.country_reason = f"Cualquier jugador disponible podía recibir este país; se asignó para evitar que {cursed_player.name} lo repita ({count} {times})."


# ── Algorithm Orchestrator ───────────────────────────────────────────────────


def calculate_matches(players: list[DraftPlayer]) -> DraftResult | None:
    """
    Core algorithm orchestrator. Returns a DraftResult,
    or None if there are not enough players to form a game.
    Raises ValueError if the GM configuration is invalid.
    """
    from .distribution import run_distribution_loop
    from .weights import build_weighted_tickets

    (estimated_tables, actual_tables, theoretical_minimum, active_gms, weighted_tickets) = (
        build_weighted_tickets(players)
    )

    if actual_tables == 0:
        return None

    # Run distribution loop first to get players properly sorted into tables
    resultado = run_distribution_loop(
        players=players,
        weighted_tickets=weighted_tickets,
        active_gms=active_gms,
        estimated_tables=estimated_tables,
        actual_tables=actual_tables,
        theoretical_minimum=theoretical_minimum,
        max_attempts=200,
    )

    # Assign countries after distribution loop completes
    if resultado is not None:
        for table in resultado.tables:
            assign_countries_to_table(table.players)

    return resultado
