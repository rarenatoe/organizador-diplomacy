from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import DraftPlayer

# ── Weighted Tickets Setup ───────────────────────────────────────────────────


def build_weighted_tickets(
    players: list[DraftPlayer],
) -> tuple[int, int, int, list[DraftPlayer], list[tuple[float, DraftPlayer]]]:
    """
    Calculates the estimated and real tables, theoretical minimum waitlist,
    active GMs, and weighted tickets list based on player priority and GM roles.

    Returns:
        tuple: (estimated_tables, actual_tables, theoretical_minimum, active_gms, weighted_tickets)
    """
    total_raw_tickets: int = sum(j.desired_games for j in players)
    estimated_tables: int = total_raw_tickets // 7

    if estimated_tables == 0:
        return 0, 0, 0, [], []

    # Handle excess GMs: limit total GM slots to estimated_tables.
    # Prioritize players who want to play less (desired_games ASC), then by gm_games DESC.
    potential_gms = [p for p in players if p.gm_games > 0]
    potential_gms.sort(key=lambda p: (p.desired_games, -p.gm_games))

    allocated_gm_slots: int = 0
    active_gms: list[DraftPlayer] = []

    for p in potential_gms:
        if allocated_gm_slots >= estimated_tables:
            p.gm_games = 0  # Cannot GM anymore
            continue

        slots_to_take = min(p.gm_games, estimated_tables - allocated_gm_slots)
        p.gm_games = slots_to_take
        allocated_gm_slots += slots_to_take
        active_gms.append(p)

    # Sorted GMs: those who referee more tables receive their assignment first.
    active_gms.sort(key=lambda j: j.gm_games, reverse=True)

    # Real game slots: GMs discounted (now safely using the capped gm_games)
    playable: dict[str, int] = {
        player.name: (
            min(player.desired_games, estimated_tables - player.gm_games)
            if player.gm_games > 0
            else player.desired_games
        )
        for player in players
    }

    # Tickets with participation weight (deterministic weights).
    #
    #   weight_after = gm_weight + slot_index + player.priority_score
    #
    #   gm_weight         = gm_games × 0.5
    #   slot_index        = 1.0 for 1st slot, 2.0 for 2nd, etc.
    #   priority_score    = continuous fraction [0.00, 0.90]
    #
    # Invariants:
    #   • First slots [1.00, 1.90] < second slots [2.00, 2.90] →
    #     nobody gets 0 participations while there's space.
    #   • Within the same slot, fewer games → lower weight → enters first.
    weighted_tickets: list[tuple[float, DraftPlayer]] = []
    for player in players:
        gm_weight: float = player.gm_games * 0.5
        priority_fraction: float = player.priority_score
        for i in range(playable[player.name]):
            weight_after: float = gm_weight + float(i + 1) + priority_fraction
            weighted_tickets.append((weight_after, player))

    actual_tables: int = len(weighted_tickets) // 7

    if actual_tables == 0:
        return estimated_tables, 0, 0, active_gms, []

    # Waitlist floor: tickets that don't fit in any scenario.
    theoretical_minimum: int = max(0, len(weighted_tickets) - actual_tables * 7)

    return estimated_tables, actual_tables, theoretical_minimum, active_gms, weighted_tickets
