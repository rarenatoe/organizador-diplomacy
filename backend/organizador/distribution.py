from __future__ import annotations

import random

from .models import DraftPlayer, DraftResult, DraftTable

# ── Distribution Logic ───────────────────────────────────────────────────────

def distribute_tickets(
    ticket_list: list[tuple[float, DraftPlayer]],
    games: list[list[DraftPlayer]],
    blocked_gms: dict[str, set[int]],
    *,
    is_new_group: bool,
) -> list[DraftPlayer]:
    """
    Distributes tickets into tables, respecting GM constraints and priority.
    """
    # Most restricted first (GMs blocked in several tables have
    # fewer options; processing them first prevents others from filling their only
    # valid table). Tie-break by weight_after.
    ticket_list.sort(
        key=lambda t: (
            -len(blocked_gms.get(t[1].name, set())),
            t[0],
        )
    )
    rejected: list[DraftPlayer] = []
    for _weight, ticket in ticket_list:
        blocked: set[int] = blocked_gms.get(ticket.name, set())
        valid_games: list[list[DraftPlayer]] = [
            g
            for i, g in enumerate(games)
            if len(g) < 7
            and not any(j.name == ticket.name for j in g)
            and i not in blocked
        ]
        if not valid_games:
            rejected.append(ticket)
            continue
        random.shuffle(valid_games)
        if is_new_group:
            valid_games.sort(key=lambda g: (sum(1 for j in g if j.is_new), len(g)))
        else:
            valid_games.sort(key=lambda g: (sum(1 for j in g if not j.is_new), len(g)))
        valid_games[0].append(ticket)
    return rejected


def run_distribution_loop(
    players: list[DraftPlayer],
    weighted_tickets: list[tuple[float, DraftPlayer]],
    active_gms: list[DraftPlayer],
    estimated_tables: int,
    actual_tables: int,
    theoretical_minimum: int,
    max_attempts: int = 200,
) -> DraftResult | None:
    """
    Runs the random distribution retry loop to find the best table arrangement.
    """
    attempts: int = 0
    best: DraftResult | None = None

    for _ in range(max_attempts):
        attempts += 1

        # Random assignment of tables to GMs
        gm_pool_indices: list[int] = list(range(estimated_tables))
        random.shuffle(gm_pool_indices)

        gm_indices: dict[str, list[int]] = {}
        ptr: int = 0
        for gm in active_gms:
            gm_indices[gm.name] = gm_pool_indices[ptr : ptr + gm.gm_games]
            ptr += gm.gm_games

        blocked_gms: dict[str, set[int]] = {
            name: set(indices) for name, indices in gm_indices.items()
        }

        # Random shuffle to break ties for tickets with same weight
        tickets_iter: list[tuple[float, DraftPlayer]] = list(weighted_tickets)
        random.shuffle(tickets_iter)
        tickets_iter.sort(key=lambda t: t[0])

        accepted_tickets = tickets_iter[: actual_tables * 7]
        initial_remaining: list[DraftPlayer] = [j for _, j in tickets_iter[actual_tables * 7 :]]

        new_tickets: list[tuple[float, DraftPlayer]] = [
            (w, j) for w, j in accepted_tickets if j.is_new
        ]
        old_tickets: list[tuple[float, DraftPlayer]] = [
            (w, j) for w, j in accepted_tickets if not j.is_new
        ]

        games: list[list[DraftPlayer]] = [[] for _ in range(actual_tables)]

        rejected_new = distribute_tickets(new_tickets, games, blocked_gms, is_new_group=True)
        rejected_old = distribute_tickets(old_tickets, games, blocked_gms, is_new_group=False)
        remaining_tickets = initial_remaining + rejected_new + rejected_old

        # Build semantic tables for this attempt
        table_to_gm: dict[int, DraftPlayer] = {}
        for name, indices in gm_indices.items():
            gm_obj: DraftPlayer = next(j for j in players if j.name == name)
            for idx in indices:
                if idx < actual_tables:
                    table_to_gm[idx] = gm_obj

        tables: list[DraftTable] = [
            DraftTable(table_number=i + 1, players=games[i], gm=table_to_gm.get(i))
            for i in range(actual_tables)
        ]

        result = DraftResult(
            tables=tables,
            waitlist_players=remaining_tickets,
            theoretical_minimum=theoretical_minimum,
        )

        if best is None or len(result.waitlist_players) < len(best.waitlist_players):
            best = result

        if len(best.waitlist_players) == theoretical_minimum:
            break  # Cannot improve further; stop early

    if best is not None:
        best.attempts_used = attempts

    return best
