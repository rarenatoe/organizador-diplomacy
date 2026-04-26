from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .models import DraftPlayer, DraftResult


class ActiveCurse(TypedDict):
    player: DraftPlayer
    country: str
    severity: int
    count: int


# ── Country Assignment Algorithm ───────────────────────────────────────────


def assign_countries_to_table(players: list[DraftPlayer]) -> None:
    """
    Assign countries using the "Greedy Intervention Minimization" strategy.
    Identifies curses based on a player's internal stats, then calculates
    the most efficient way to resolve them using either Self-Assignment or Shielding,
    minimizing the total number of forced assignments at the table.
    """
    # Initialize all players with no country
    for player in players:
        player.country = ""
        player.country_reason = []

    countries = ["England", "France", "Germany", "Italy", "Austria", "Russia", "Turkey"]

    # 1. Identify all active curses based purely on the player's PERSONAL statistics
    active_curses: list[ActiveCurse] = []
    for player in players:
        counts = {c: getattr(player, f"c_{c.lower()}", 0) for c in countries}
        if not counts:
            continue

        # The baseline is the player's own least-played country
        min_count = min(counts.values())

        for country, count in counts.items():
            # A curse is any country played 2+ times more than their personal baseline
            if count >= min_count + 2:
                active_curses.append(
                    {
                        "player": player,
                        "country": country,
                        "severity": count - min_count,
                        "count": count,
                    }
                )

    # 2. Greedy Resolution Loop: Find the single assignment that resolves the most curses
    while active_curses:
        best_assignment = None
        # Score format: (curses_resolved, severity_resolved, -player_historical_count)
        best_score = (-1, -1, float("-inf"))

        unassigned_players = [p for p in players if p.country == ""]
        available_countries = [c for c in countries if not any(p.country == c for p in players)]

        for p in unassigned_players:
            p_counts = {c: getattr(p, f"c_{c.lower()}", 0) for c in available_countries}
            if not p_counts:
                continue

            p_min_all = min(getattr(p, f"c_{c.lower()}", 0) for c in countries)

            for c in available_countries:
                p_c_count = p_counts[c]

                # A player cannot be assigned a country they are currently cursed for
                if p_c_count >= p_min_all + 2:
                    continue

                # Calculate how many curses THIS specific assignment resolves
                # Tool B (Self): Resolves all curses belonging to this player
                # Tool A (Shield): Resolves all curses involving this country for other players
                resolved = [
                    curse
                    for curse in active_curses
                    if curse["player"] == p or curse["country"] == c
                ]

                if not resolved:
                    continue

                num_resolved = len(resolved)
                severity_resolved = sum(curse["severity"] for curse in resolved)

                # Tie-breaker: prioritize assigning the player to their absolute lowest historical country
                self_healing_score = -p_c_count

                score = (num_resolved, severity_resolved, self_healing_score)

                if score > best_score:
                    best_score = score
                    best_assignment = (p, c, resolved)

        if not best_assignment:
            # No valid assignments left that can resolve remaining curses (gridlock defense)
            break

        assignee, country_to_assign, resolved_curses = best_assignment

        # Apply the optimal assignment
        assignee.country = country_to_assign

        # Generate an intelligent explanation for the GM based on which tools triggered
        reasons: list[str] = []
        self_curses = [rc for rc in resolved_curses if rc["player"] == assignee]
        shield_curses = [
            rc
            for rc in resolved_curses
            if rc["country"] == country_to_assign and rc["player"] != assignee
        ]

        if self_curses:
            c_names = ", ".join(rc["country"] for rc in self_curses)
            reasons.append(f"Auto-asignación estratégica para evitar que reciba {c_names}.")

        if shield_curses:
            p_names = ", ".join(rc["player"].name for rc in shield_curses)
            reasons.append(f"Actúa de escudo para evitar que {p_names} repitan este país.")

        assignee.country_reason = reasons

        # Remove the resolved curses from the pool
        active_curses = [curse for curse in active_curses if curse not in resolved_curses]


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
