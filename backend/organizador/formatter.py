"""
formatter.py – Pure text generation for game results.

All functions return strings or lists of strings. No file I/O.

Functions:
  format_copypaste              → share-ready text; stored in game_events.copypaste_text
  format_result                 → detailed event results for terminal output
  build_projection              → per-player games_this_year projection table
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import DraftPlayer, DraftResult, DraftTable

SEP: str = "─" * 44

# Country name translations from English to Spanish
_COUNTRY_TRANSLATIONS: dict[str, str] = {
    "England": "Inglaterra",
    "France": "Francia", 
    "Germany": "Alemania",
    "Italy": "Italia",
    "Austria": "Austria",
    "Russia": "Rusia",
    "Turkey": "Turquía"
}

def translate_country(country: str) -> str:
    """Translate English country name to Spanish."""
    if not country or country == "":
        return ""
    return _COUNTRY_TRANSLATIONS.get(country, country)


# ── Share section ──────────────────────────────────────────────────────────────

def format_copypaste(result: DraftResult) -> str:
    """
    Section ready to copy-paste (WhatsApp, Discord, etc.).
    Names only — no experience metadata or decorations.
    """
    return format_copypaste_from_dict(result.model_dump())


def format_copypaste_from_dict(result_dict: dict[str, Any]) -> str:
    """
    Section ready to copy-paste from a dictionary representation.
    """
    lines: list[str] = []
    for table in result_dict.get("tables", []):
        gm_name = table.get("gm", {}).get("name") if table.get("gm") else None
        gm_str: str = f"  |  GM: {gm_name}" if gm_name else ""
        lines.append(f"Partida {table['table_number']}{gm_str}")

        # Track footnotes for this table
        footnotes: dict[str, str] = {}
        footnote_counter = 0

        for i, player in enumerate(table.get("players", [])):
            country = player.get("country")
            country_reason = player.get("country_reason")
            if country:
                translated = translate_country(country)
                if country_reason:
                    # Get or create footnote marker for this reason
                    if country_reason not in footnotes:
                        footnote_counter += 1
                        footnotes[country_reason] = "*" * footnote_counter
                    marker = footnotes[country_reason]
                    country_str = f" ({translated}{marker})"
                else:
                    country_str = f" ({translated})"
            else:
                country_str = ""
            lines.append(f"  {i + 1}. {player['name']}{country_str}")

        # Add footnotes if any
        if footnotes:
            lines.append("")
            for reason, marker in footnotes.items():
                lines.append(f"{marker} {reason}")

        lines.append("")
    
    remaining = result_dict.get("waitlist_players", [])
    if remaining:
        lines.append("Lista de espera:")
        seen: set[str] = set()
        for j in remaining:
            name = j["name"]
            if name not in seen:
                seen.add(name)
                lines.append(f"  - {name}")
    return "\n".join(lines)


# ── Detail section ─────────────────────────────────────────────────────────────

def format_result(
    result: DraftResult,
    sep: str = SEP,
) -> list[str]:
    """Returns lines for the DETAIL DEL EVENTO section."""
    lines: list[str] = [
        f"  SE GENERARON {len(result.tables)} PARTIDA(S)",
        sep,
    ]

    for table in result.tables:
        new_players: int = sum(1 for j in table.players if j.is_new)
        old_players: int = sum(1 for j in table.players if not j.is_new)
        gm_str: str = f"GM: {table.gm.name}" if table.gm else "⚠️  Sin GM asignado"
        lines.append(f"\n[ Partida {table.table_number} ]  Nuevos: {new_players}  Antiguos: {old_players}  {gm_str}")

        # Track footnotes for this table
        footnotes: dict[str, str] = {}
        footnote_counter = 0

        for j, player in enumerate(table.players):
            country_str = ""
            if player.country:
                translated = translate_country(player.country)
                if player.country_reason:
                    # Get or create footnote marker for this reason
                    if player.country_reason not in footnotes:
                        footnote_counter += 1
                        footnotes[player.country_reason] = "*" * footnote_counter
                    marker = footnotes[player.country_reason]
                    country_str = f" ({translated}{marker})"
                else:
                    country_str = f" ({translated})"
            label: str = "Nuevo" if player.is_new else f"Antiguo ({player.games_this_year} juegos)"
            lines.append(f"  {j + 1}. {player.name}{country_str}  —  {label}")

        # Add footnotes if any
        if footnotes:
            lines.append("")
            for reason, marker in footnotes.items():
                lines.append(f"  {marker} {reason}")

    # Unique GMs who referee at least one table, in order of appearance
    gms_seen: set[str] = set()
    active_gms: list[DraftPlayer] = []
    for table in result.tables:
        if table.gm and table.gm.name not in gms_seen:
            gms_seen.add(table.gm.name)
            active_gms.append(table.gm)

    if active_gms:
        lines += [f"\n{sep}", "  GAME MASTERS", sep]
        for gm in active_gms:
            gm_tables: list[DraftTable] = [
                t for t in result.tables if t.gm and t.gm.name == gm.name
            ]
            tables_str: str = ", ".join(f"Partida {t.table_number}" for t in gm_tables)
            tables_as_player: int = sum(
                1 for t in result.tables
                if any(j is gm for j in t.players)
            )
            lines.append(
                f"  {gm.name}: arbitra {tables_str}  "
                f"(quería jugar {gm.desired_games}, jugará {tables_as_player})"
            )

    if result.waitlist_players:
        lines += [f"\n{sep}", "  JUGADORES EN LISTA DE ESPERA", sep]
        count: Counter[str] = Counter(t.name for t in result.waitlist_players)
        for name, slots in count.items():
            suffix = f"{slots} cupo(s) sin asignar" if slots > 1 else "1 cupo sin asignar"
            lines.append(f"  - {name}  ({suffix})")

    return lines


# ── Projection section ─────────────────────────────────────────────────────────

def build_projection(
    result: DraftResult,
    players: list[DraftPlayer],
) -> list[str]:
    """
    Projects each player's games_this_year after this event.

    Counts:
      +1 per table played as a player.
      +0 for GMing (GMing does not add to games_this_year; role is
           reflected in algorithm's weight system with a 0.5 factor).
    """
    slots_played: Counter[str] = Counter(
        j.name for table in result.tables for j in table.players
    )
    gm_slots: Counter[str] = Counter(
        table.gm.name for table in result.tables if table.gm is not None
    )

    rows: list[tuple[int, str, int, int, int, int]] = []
    for player in players:
        played: int = slots_played[player.name]
        as_gm: int = gm_slots[player.name]
        current: int = int(player.games_this_year)
        projected: int = current + played
        rows.append((projected, player.name, current, played, as_gm, projected))

    rows.sort(key=lambda r: (-r[0], r[1]))

    width: int = max(len(r[1]) for r in rows)
    header: str = f"  {'Player':{width}}  Actual  +Play  +GM  Projected"
    lines: list[str] = [header, "  " + "-" * (len(header) - 2)]
    for _, name, current, played, as_gm, projected in rows:
        lines.append(
            f"  {name:{width}}    {current:>3}     {played:>3}   {as_gm:>2}         {projected:>3}"
        )

    return lines
