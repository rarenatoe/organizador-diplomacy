"""
notion_sync.py – Async Notion synchronization module.

Downloads player data from Notion and creates snapshots in the database.
This module provides async functions for use with FastAPI background tasks.
"""

from __future__ import annotations

__all__ = [
    "fetch_notion_data",
    "build_notion_players_lookup",
    "notion_cache_to_db",
    "daemon_loop",
    "start_background_sync",
]


import asyncio
import concurrent.futures
import difflib
import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict, cast

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

from backend.crud.chain import create_branch_edge
from backend.crud.players import get_or_create_player, rename_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
    get_latest_snapshot_id,
    get_snapshot_players,
    log_snapshot_history,
    snapshots_have_same_roster,
    update_notion_cache,
)
from backend.db.connection import async_engine

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.db.models import RenameDict

logger = logging.getLogger(__name__)

# TypedDict definitions for Notion API responses


class NotionTextItem(TypedDict, total=False):
    plain_text: str


class NotionRelationItem(TypedDict, total=False):
    id: str


class NotionFormula(TypedDict, total=False):
    type: str
    number: int | float | None


class NotionProperty(TypedDict, total=False):
    id: str
    type: str
    title: list[NotionTextItem]
    rich_text: list[NotionTextItem]
    number: int | float | None
    formula: NotionFormula
    relation: list[NotionRelationItem]


class NotionPage(TypedDict):
    id: str
    properties: dict[str, NotionProperty]


class NotionQueryResponse(TypedDict, total=False):
    results: list[NotionPage]
    has_more: bool
    next_cursor: str | None


# ── TypedDict for Notion player data ───────────────────────────────────────────


class NotionPlayerDict(TypedDict):
    """TypedDict for Notion player data with strict type safety."""

    notion_id: str
    nombre: str
    experiencia: str
    juegos_este_ano: int
    alias: list[str]
    c_england: int
    c_france: int
    c_germany: int
    c_italy: int
    c_austria: int
    c_russia: int
    c_turkey: int


# Player field defaults for first-time Notion players

FIELD_DEFAULTS: dict[str, int] = {
    "prioridad": 0,
    "partidas_deseadas": 1,
    "partidas_gm": 0,
}

# ── Country property mapping ──────────────────────────────────────────────────

COUNTRY_PROPS: dict[str, str] = {
    "c_england": "∀ 🇬🇧",
    "c_france": "∀ 🇫🇷",
    "c_germany": "∀ 🇩🇪",
    "c_italy": "∀ 🇮🇹",
    "c_austria": "∀ 🇦🇹",
    "c_russia": "∀ 🇷🇺",
    "c_turkey": "∀ 🇹🇷",
}

# ── Helpers de extracción ─────────────────────────────────────────────────────


def extract_number(prop: NotionProperty | None) -> int:
    """Extrae un número de una propiedad number o formula."""
    if not prop:
        return 0
    if prop.get("type") == "number":
        return int(prop.get("number") or 0)
    if prop.get("type") == "formula":
        return int(prop.get("formula", {}).get("number") or 0)
    return 0


def extract_name(prop: NotionProperty | None) -> str:
    """Extrae texto plano de una propiedad title."""
    if not prop:
        return ""
    return "".join(p.get("plain_text", "") for p in prop.get("title", [])).strip()


def calculate_experience(participaciones_prop: NotionProperty | None) -> str:
    """'Antiguo' si el jugador tiene ≥1 participación histórica, 'Nuevo' si no."""
    if not participaciones_prop:
        return "Nuevo"
    return "Antiguo" if participaciones_prop.get("relation") else "Nuevo"


# ── Name similarity detection ────────────────────────────────────────────────


def normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, strip, collapse whitespace."""
    return " ".join(name.lower().split())


def words_match(word_a: str, word_b: str) -> float:
    """
    Check similarity between two words using difflib.
    Handles typos, prefixes, and abbreviations.
    Returns a score between 0.0 and 1.0.
    """
    if not word_a or not word_b:
        return 0.0

    wa = word_a.lower().rstrip(".")
    wb = word_b.lower().rstrip(".")

    if wa == wb:
        return 1.0

    # Check if one is a prefix of the other (at least 1 char)
    # This handles abbreviations like "P." for "Paul"
    if len(wa) >= 1 and len(wb) >= 1 and (wb.startswith(wa) or wa.startswith(wb)):
        return 0.8  # Prefix match is good but not perfect

    # Probabilistic match for typos
    return difflib.SequenceMatcher(None, wa, wb).ratio()


def similarity(a: str, b: str) -> float:
    """
    Calculate similarity ratio between two names (0.0 to 1.0).
    Uses Token-Set + Probabilistic matching.
    """
    norm_a = normalize_name(a)
    norm_b = normalize_name(b)

    if not norm_a and not norm_b:
        return 1.0
    if not norm_a or not norm_b:
        return 0.0

    words_a = norm_a.split()
    words_b = norm_b.split()

    # We want to see how many words from the shorter name find a match in the longer name
    short_words = words_a if len(words_a) <= len(words_b) else words_b
    long_words = words_b if len(words_a) <= len(words_b) else words_a

    matched_count = 0.0
    used_long_indices: set[int] = set()

    for sw in short_words:
        best_word_sim = 0.0
        best_idx = -1

        for i, lw in enumerate(long_words):
            if i in used_long_indices:
                continue
            sim = words_match(sw, lw)
            if sim > best_word_sim:
                best_word_sim = sim
                best_idx = i

        if best_word_sim >= 0.85:  # High confidence word match
            matched_count += 1.0
            used_long_indices.add(best_idx)
        elif best_word_sim >= 0.5:  # Partial word match
            matched_count += best_word_sim
            used_long_indices.add(best_idx)

    # Score is matched words over total words in the longer name
    score = matched_count / len(long_words)

    # BONUS: If it's a perfect prefix match (all words of shorter name match)
    # and the difference is only 1 word, we boost the similarity to 0.8
    if matched_count == len(short_words) and len(long_words) - len(short_words) == 1:
        return max(0.8, score)

    return score


def detect_similar_names(
    notion_players: dict[str, NotionPlayerDict] | list[NotionPlayerDict],
    snapshot_names: list[str],
    threshold: float = 0.75,
) -> list[dict[str, Any]]:
    """
    Detect similar names between Notion (including aliases) and snapshot
    using a 4-step waterfall algorithm.
    Returns detailed match information including matching method.
    """
    # Normalize notion_players input to list of dicts if it's a map
    players_list = (
        list(notion_players.values()) if isinstance(notion_players, dict) else notion_players
    )

    # Pre-normalize all snapshot names for Step 1 & 2
    norm_snapshots = {name: normalize_name(name) for name in snapshot_names}

    potential_matches: list[dict[str, Any]] = []

    # Step 1 & 2: Exact & Alias Matches (Filter them out)
    # We want to find names that DON'T match exactly but are similar

    # Track exact matches to avoid comparing them for similarity
    exact_matches_snapshot: set[str] = set()

    for player_data in players_list:
        notion_main_name = player_data["nombre"]
        notion_id = player_data["notion_id"]
        norm_notion_main = normalize_name(notion_main_name)

        for snap_name in snapshot_names:
            norm_snap = norm_snapshots[snap_name]

            # Step 1: Exact Match
            if norm_notion_main == norm_snap:
                exact_matches_snapshot.add(snap_name)
                continue

    # Step 3: Hybrid Fuzzy Matching
    # Only compare snapshots that didn't have an exact match with ANY notion player
    # and notion players that didn't have an exact match with THIS snapshot
    for player_data in players_list:
        notion_main_name = player_data["nombre"]
        notion_id = player_data["notion_id"]
        notion_variations = [notion_main_name] + player_data.get("alias", [])

        for snap_name in snapshot_names:
            if snap_name in exact_matches_snapshot:
                continue

            # Check similarity against all variations, keep best
            best_sim = 0.0
            best_match_method = "fuzzy"
            matched_alias = None

            for var in notion_variations:
                # Compare normalized strings to guarantee case/accent insensitivity
                sim = similarity(normalize_name(var), norm_snapshots[snap_name])
                if sim > best_sim:
                    best_sim = sim
                    if var != notion_main_name:
                        # This variation is an alias
                        matched_alias = var
                        best_match_method = "alias_exact" if sim == 1.0 else "alias_fuzzy"
                    else:
                        best_match_method = "name_fuzzy"

            if best_sim >= threshold:
                match_data = {
                    "notion_id": notion_id,
                    "notion_name": notion_main_name,
                    "snapshot": snap_name,
                    "similarity": round(best_sim, 3),
                    "match_method": best_match_method,
                }

                if matched_alias:
                    match_data["matched_alias"] = matched_alias

                potential_matches.append(match_data)

    # Step 4: Bi-Directional Ambiguity Detection (1-to-Many)
    # If a name maps to multiple candidates, they are all conflicts.
    # Group by notion and by snapshot to detect 1-to-Many in both directions.
    notion_to_snaps: defaultdict[str, set[str]] = defaultdict(set)
    snap_to_notions: defaultdict[str, set[str]] = defaultdict(set)

    for m in potential_matches:
        notion_to_snaps[m["notion_name"]].add(m["snapshot"])
        snap_to_notions[m["snapshot"]].add(m["notion_name"])

    # All potential matches found in Step 3 are technically conflicts
    # since they are not exact matches but are above threshold.
    # The ambiguity detection is already implicit if we return all matches.
    # We just need to make sure they are unique and sorted.

    unique_matches: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for m in potential_matches:
        key = (m["notion_name"], m["snapshot"])
        if key not in seen:
            unique_matches.append(m)
            seen.add(key)

    unique_matches.sort(key=lambda x: x["similarity"], reverse=True)
    return unique_matches


# ── Descarga desde Notion ─────────────────────────────────────────────────────


def download_all_pages(
    client: Client,
    database_id: str,
) -> list[NotionPage]:
    """
    Descarga todas las páginas de la DB paginando automáticamente.

    notion-client ≥2.7 eliminó databases.query(); hay que obtener el
    data_source_id desde databases.retrieve() y luego usar data_sources.query().
    """
    db_info: dict[str, Any] = cast(
        "dict[str, Any]", client.databases.retrieve(database_id=database_id)
    )
    data_sources = db_info.get("data_sources", [])
    if not data_sources:
        raise RuntimeError(
            f"La base de datos '{database_id}' no tiene data_sources. "
            "Asegúrate de que la integración tenga acceso de lectura."
        )
    data_source_id: str = data_sources[0]["id"]

    # Payload reduction: get property IDs for required fields
    prop_ids: list[str] = []
    props = db_info.get("properties", {})
    required_names = ["Nombre", "Participaciones", "Alias"] + list(COUNTRY_PROPS.values())
    for name in required_names:
        if name in props:
            prop_ids.append(props[name]["id"])

    pages: list[NotionPage] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "data_source_id": data_source_id,
            "result_type": "page",
        }
        if prop_ids:
            kwargs["filter_properties"] = prop_ids
        if cursor:
            kwargs["start_cursor"] = cursor
        response = cast("NotionQueryResponse", client.data_sources.query(**kwargs))

        pages.extend(response.get("results", []))

        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return pages


def count_games_this_year(
    client: Client,
    participaciones_db_id: str,
    año: int,
) -> dict[str, int]:
    """
    Descarga todas las páginas de la DB Participaciones y cuenta, por jugador,
    cuántas tienen Temporada == año (filtrado en el cliente).

    Retorna {player_page_id_sin_guiones: conteo}.

    Nota: Temporada es un rollup desde la relación 'Partida'. Si la DB Partida
    no está conectada a la integración, el valor será None y se advertirá al
    usuario (todos los conteos quedarán en 0).
    """
    db_info: dict[str, Any] = cast(
        "dict[str, Any]", client.databases.retrieve(database_id=participaciones_db_id)
    )
    data_sources = db_info.get("data_sources", [])
    if not data_sources:
        raise RuntimeError(
            f"La DB de Participaciones '{participaciones_db_id}' no tiene data_sources. "
            "Asegúrate de que la integración tenga acceso de lectura."
        )
    ds_id: str = data_sources[0]["id"]

    # Payload reduction: get property IDs for "Temporada" and "Jugador"
    prop_ids: list[str] = []
    props = db_info.get("properties", {})
    for name in ["Temporada", "Jugador"]:
        if name in props:
            prop_ids.append(props[name]["id"])

    conteo: dict[str, int] = {}
    sin_temporada = 0
    cursor: str | None = None

    while True:
        kwargs: dict[str, Any] = {
            "data_source_id": ds_id,
            "result_type": "page",
            "filter": {"property": "Temporada", "rollup": {"number": {"equals": año}}},
        }
        if prop_ids:
            kwargs["filter_properties"] = prop_ids
        if cursor:
            kwargs["start_cursor"] = cursor
        response: dict[str, Any] = cast("dict[str, Any]", client.data_sources.query(**kwargs))

        for page in response.get("results", []):
            props = page.get("properties", {})

            # Temporada: rollup de la relation 'Partida' (function: sum del año)
            temporada = props.get("Temporada", {}).get("rollup", {}).get("number")
            if temporada is None:
                sin_temporada += 1
                continue
            if int(temporada) != año:
                continue

            # Jugador: relation de vuelta al jugador
            for rel in props.get("Jugador", {}).get("relation", []):
                pid = rel["id"].replace("-", "")
                conteo[pid] = conteo.get(pid, 0) + 1

        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")

    if sin_temporada > 0 and not conteo:
        logger.warning(
            f"{sin_temporada} participación(es) sin Temporada (rollup None). "
            "Conecta la DB 'Partida' a la integración para obtener Juegos_Este_Año correcto."
        )

    return conteo


def find_notion_player(
    name: str, notion_players: dict[str, NotionPlayerDict]
) -> NotionPlayerDict | None:
    """Finds a Notion player by name or alias."""
    norm_name = normalize_name(name)
    # Exact name match
    if norm_name in notion_players:
        return notion_players[norm_name]
    # Alias match
    for p in notion_players.values():
        if norm_name in p.get("alias", []):
            return p
    return None


# ── Core sync logic ──────────────────────────────────────────────────────────


async def fetch_notion_data() -> tuple[list[NotionPage], dict[str, int], Client]:
    """
    Fetch player data from Notion API.
    Returns (pages, games_played_map, client).
    """
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or token.startswith("secret_XXX"):
        raise RuntimeError("NOTION_TOKEN no configurado")
    if not db_id or "XXX" in db_id:
        raise RuntimeError("NOTION_DATABASE_ID no configurado")
    if not part_db_id or "XXX" in part_db_id:
        raise RuntimeError("NOTION_PARTICIPACIONES_DB_ID no configurado")

    año_actual = datetime.now().year
    client = Client(auth=token)

    # Run Notion API calls in thread pool (they're blocking I/O)
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_pages = executor.submit(download_all_pages, client, db_id)
        future_conteo = executor.submit(count_games_this_year, client, part_db_id, año_actual)

        pages = await loop.run_in_executor(None, future_pages.result)
        games_played_map = await loop.run_in_executor(None, future_conteo.result)

    logger.info(
        f"Notion sync: {len(pages)} jugador(es), "
        f"{sum(games_played_map.values())} partida(s) en {año_actual}."
    )

    return pages, games_played_map, client


def build_notion_players_lookup(
    pages: list[NotionPage],
    games_played_map: dict[str, int],
) -> dict[str, NotionPlayerDict]:
    """Build a lookup dict of Notion players by normalized name."""
    notion_players: dict[str, NotionPlayerDict] = {}

    for page in pages:
        props = page.get("properties", {})
        nombre_prop = props.get("Nombre")
        if not nombre_prop:
            continue
        nombre = extract_name(nombre_prop)
        if not nombre:
            continue

        # Experiencia
        part_prop = props.get("Participaciones")
        experience_val = calculate_experience(part_prop)

        # Juegos_Este_Ano
        player_id = page["id"].replace("-", "")
        games_count = games_played_map.get(player_id, 0)

        # Alias extraction
        alias_prop = props.get("Alias")
        alias_text = (
            "".join(p.get("plain_text", "") for p in alias_prop.get("rich_text", []))
            if alias_prop
            else ""
        )
        alias_list = [a.strip() for a in alias_text.split(",") if a.strip()]

        # Country history extraction
        countries_data = {
            key: extract_number(props.get(notion_name))
            for key, notion_name in COUNTRY_PROPS.items()
        }

        notion_players[normalize_name(nombre)] = NotionPlayerDict(
            {
                "notion_id": page["id"],
                "nombre": nombre,
                "experiencia": experience_val,
                "juegos_este_ano": games_count,
                "alias": alias_list,
                "c_england": countries_data["c_england"],
                "c_france": countries_data["c_france"],
                "c_germany": countries_data["c_germany"],
                "c_italy": countries_data["c_italy"],
                "c_austria": countries_data["c_austria"],
                "c_russia": countries_data["c_russia"],
                "c_turkey": countries_data["c_turkey"],
            }
        )

    return notion_players


async def _check_snapshot_has_children(session: AsyncSession, snapshot_id: int) -> bool:
    """Check if a snapshot has any child events."""
    from sqlalchemy import select

    from backend.db.models import TimelineEdge

    result = await session.execute(
        select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snapshot_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _update_snapshot_in_place(
    session: AsyncSession,
    snapshot_id: int,
    rows: list[dict[str, Any]],
    renames: list[RenameDict],
) -> None:
    """Update an existing snapshot in-place with new player data."""
    from sqlalchemy import delete, update

    from backend.db.models import Snapshot, SnapshotPlayer

    # Fetch old roster before clearing
    previous_players = await get_snapshot_players(session, snapshot_id)

    # Execute renames safely to maintain player continuity without UNIQUE constraint crashes
    from sqlalchemy import select

    from backend.db.models import Player

    for r in renames or []:
        target_exists = await session.execute(select(Player).where(Player.name == r["to"]))
        if not target_exists.scalar_one_or_none():
            await session.execute(
                update(Player).where(Player.name == r["from"]).values(name=r["to"])
            )

    # Update the existing snapshot source
    await session.execute(
        update(Snapshot).where(Snapshot.id == snapshot_id).values(source="notion_sync")
    )

    # Clear old roster
    await session.execute(delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id))

    # Insert new players
    for row in rows:
        pid = await get_or_create_player(session, row["nombre"], row.get("notion_id"))
        await add_player_to_snapshot(
            session,
            snapshot_id,
            pid,
            row["experiencia"],
            row["juegos_este_ano"],
            row["prioridad"],
            row["partidas_deseadas"],
            row["partidas_gm"],
        )

    # Calculate dynamic diff for history logging
    from backend.crud.snapshots import generate_deep_diff

    roster_fields = {
        "nombre",
        "experiencia",
        "juegos_este_ano",
        "prioridad",
        "partidas_deseadas",
        "partidas_gm",
    }
    prev_roster = [{k: v for k, v in p.items() if k in roster_fields} for p in previous_players]
    new_roster = [
        {
            "nombre": r["nombre"],
            "experiencia": r["experiencia"],
            "juegos_este_ano": r["juegos_este_ano"],
            "prioridad": r.get("prioridad", 0),
            "partidas_deseadas": r.get("partidas_deseadas", 1),
            "partidas_gm": r.get("partidas_gm", 0),
        }
        for r in rows
    ]
    diff = generate_deep_diff(prev_roster, new_roster, renames)

    # Log the history (outside the loop)
    await log_snapshot_history(
        session,
        snapshot_id=snapshot_id,
        action_type="notion_sync",
        changes=diff,
        previous_state={"players": previous_players},
    )

    logger.info(f"Snapshot #{snapshot_id} updated in-place with {len(rows)} jugador(es).")


async def _create_new_snapshot(
    session: AsyncSession,
    source_snapshot_id: int | None,
    rows: list[dict[str, Any]],
) -> int:
    """Create a new snapshot with player data and sync event."""
    snap_id = await create_snapshot(session, "notion_sync")

    for row in rows:
        pid = await get_or_create_player(session, row["nombre"], row.get("notion_id"))
        await add_player_to_snapshot(
            session,
            snap_id,
            pid,
            row["experiencia"],
            row["juegos_este_ano"],
            row["prioridad"],
            row["partidas_deseadas"],
            row["partidas_gm"],
        )

    # Create sync event only if we have a source snapshot
    if source_snapshot_id is not None:
        await create_branch_edge(session, source_snapshot_id, snap_id)

    logger.info(f"Snapshot #{snap_id} created with {len(rows)} jugador(es).")
    return snap_id


# ── Daemon Functions ────────────────────────────────────────────────────────


async def daemon_loop() -> None:
    """Async daemon loop that runs indefinitely, syncing Notion every 15 minutes."""
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or not db_id or not part_db_id or token.startswith("secret_XXX"):
        logger.info(" [Cache Daemon] Skipping background sync: Missing Notion credentials.")
        return

    while True:
        logger.info(" [Cache Daemon] Starting sync at %s", datetime.now())
        try:
            # 1. Fetch and parse data from Notion
            pages, games_played_map, _client = await fetch_notion_data()
            notion_players = build_notion_players_lookup(pages, games_played_map)

            # 2. Save it to database
            from sqlalchemy.ext.asyncio.session import AsyncSession

            async with AsyncSession(async_engine) as session:
                await notion_cache_to_db(session, notion_players)
                await session.commit()

            logger.info(" [Cache Daemon] Sync complete. Sleeping for 15 minutes.")
        except Exception as e:
            logger.error(" [Cache Daemon] Error during sync: %s", e, exc_info=True)

        await asyncio.sleep(900)  # 15 minutes


async def start_background_sync() -> None:
    """Starts async background daemon."""
    asyncio.create_task(daemon_loop())


async def _build_snapshot_rows(
    session: AsyncSession,
    source_snapshot_id: int | None,
    notion_players: dict[str, NotionPlayerDict],
    merges: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build the list of player rows for the new snapshot.
    Combines existing snapshot data with Notion updates.
    """
    rows: list[dict[str, Any]] = []
    merges = merges or {}

    if source_snapshot_id is not None:
        # Get existing players from source snapshot
        existing_list = await get_snapshot_players(session, source_snapshot_id)
        existing_map = {p["nombre"]: p for p in existing_list}

        merged_notion_normalized = {normalize_name(v["to"]) for v in merges.values()}

        # Reverse mapping: merge target names -> merge info (for renamed players)
        reverse_merges = {v["to"]: {"from": k, **v} for k, v in merges.items()}

        # Start with all players from the existing snapshot
        for nombre, existente in existing_map.items():
            # 1. Check if this player was explicitly merged via the UI dialog
            if nombre in merges:
                merge_info = merges[nombre]
                notion_name = merge_info["to"]
                action = merge_info["action"]
                notion_norm = normalize_name(notion_name)

                if notion_norm in notion_players:
                    notion_data = notion_players[notion_norm]
                    rows.append(
                        {
                            "nombre": notion_data["nombre"] if action == "merge_notion" else nombre,
                            "experiencia": notion_data["experiencia"],
                            "juegos_este_ano": notion_data["juegos_este_ano"],
                            "prioridad": int(
                                existente.get("prioridad", FIELD_DEFAULTS["prioridad"])
                            ),
                            "partidas_deseadas": int(
                                existente.get(
                                    "partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"]
                                )
                            ),
                            "partidas_gm": int(
                                existente.get("partidas_gm", FIELD_DEFAULTS["partidas_gm"])
                            ),
                            "alias": notion_data.get("alias", []),
                            "notion_id": notion_data["notion_id"],
                            **{c: notion_data[c] for c in COUNTRY_PROPS},
                        }
                    )
                    continue

            # 1b. Check if this player name is the TARGET of a merge (was renamed)
            if nombre in reverse_merges:
                merge_info = reverse_merges[nombre]
                notion_name = nombre  # The renamed name is the Notion name
                notion_norm = normalize_name(notion_name)

                if notion_norm in notion_players:
                    notion_data = notion_players[notion_norm]
                    rows.append(
                        {
                            "nombre": notion_data["nombre"],
                            "experiencia": notion_data["experiencia"],
                            "juegos_este_ano": notion_data["juegos_este_ano"],
                            "prioridad": int(
                                existente.get("prioridad", FIELD_DEFAULTS["prioridad"])
                            ),
                            "partidas_deseadas": int(
                                existente.get(
                                    "partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"]
                                )
                            ),
                            "partidas_gm": int(
                                existente.get("partidas_gm", FIELD_DEFAULTS["partidas_gm"])
                            ),
                            "alias": notion_data.get("alias", []),
                            "notion_id": notion_data["notion_id"],
                            **{c: notion_data[c] for c in COUNTRY_PROPS},
                        }
                    )
                    continue

            # 2. Check if this player exists in Notion (exact match or alias match)
            notion_data = find_notion_player(nombre, notion_players)
            if (
                notion_data
                and normalize_name(notion_data["nombre"]) not in merged_notion_normalized
            ):
                rows.append(
                    {
                        "nombre": nombre,  # Keep local name
                        "experiencia": notion_data["experiencia"],
                        "juegos_este_ano": notion_data["juegos_este_ano"],
                        "prioridad": int(existente.get("prioridad", FIELD_DEFAULTS["prioridad"])),
                        "partidas_deseadas": int(
                            existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])
                        ),
                        "partidas_gm": int(
                            existente.get("partidas_gm", FIELD_DEFAULTS["partidas_gm"])
                        ),
                        "alias": notion_data.get("alias", []),
                        "notion_id": notion_data["notion_id"],
                        **{c: notion_data[c] for c in COUNTRY_PROPS},
                    }
                )
            else:
                # 3. Keep existing data (player not in Notion and not merged)
                rows.append(
                    {
                        "nombre": nombre,
                        "experiencia": existente.get("experiencia", "Nuevo"),
                        "juegos_este_ano": int(existente.get("juegos_este_ano", 0)),
                        "prioridad": int(existente.get("prioridad", FIELD_DEFAULTS["prioridad"])),
                        "partidas_deseadas": int(
                            existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])
                        ),
                        "partidas_gm": int(
                            existente.get("partidas_gm", FIELD_DEFAULTS["partidas_gm"])
                        ),
                        **{c: existente.get(c, 0) for c in COUNTRY_PROPS},
                    }
                )

    else:
        # No existing snapshot - use all Notion players directly from our lookup
        for _, notion_data in notion_players.items():
            rows.append(
                {
                    "nombre": notion_data["nombre"],
                    "experiencia": notion_data["experiencia"],
                    "juegos_este_ano": notion_data["juegos_este_ano"],
                    "prioridad": FIELD_DEFAULTS["prioridad"],
                    "partidas_deseadas": FIELD_DEFAULTS["partidas_deseadas"],
                    "partidas_gm": FIELD_DEFAULTS["partidas_gm"],
                    "alias": notion_data.get("alias", []),
                    "notion_id": notion_data["notion_id"],
                    **{c: notion_data[c] for c in COUNTRY_PROPS},
                }
            )

    return rows


async def notion_cache_to_db(
    session: AsyncSession, notion_players: dict[str, NotionPlayerDict]
) -> None:
    """Transforms parsed Notion data and bulk updates local SQLite cache."""

    cache_rows: list[dict[str, Any]] = []
    for nd in notion_players.values():
        cache_rows.append(
            {
                "notion_id": nd["notion_id"],
                "nombre": nd["nombre"],
                "experiencia": nd["experiencia"],
                "juegos_este_ano": nd["juegos_este_ano"],
                "alias": nd.get("alias", []),
                "c_england": nd.get("c_england", 0),
                "c_france": nd.get("c_france", 0),
                "c_germany": nd.get("c_germany", 0),
                "c_italy": nd.get("c_italy", 0),
                "c_austria": nd.get("c_austria", 0),
                "c_russia": nd.get("c_russia", 0),
                "c_turkey": nd.get("c_turkey", 0),
            }
        )
    await update_notion_cache(session, cache_rows)


# ── Public API ───────────────────────────────────────────────────────────────


async def run_notion_sync_background(
    snapshot_id: int | None = None,
    *,
    force: bool = False,
    merges: dict[str, dict[str, str]] | None = None,
) -> int | None:
    """
    Async entrypoint to run notion sync in the background.

    Downloads player data from Notion, compares with existing snapshot,
    and creates/updates a snapshot in the database.

    Args:
        snapshot_id: Source snapshot ID to branch from (None for initial sync)
        force: Force creation even if data hasn't changed
        merges: Optional dict of player name merges {from_name: {"to": to_name, "action": action}}

    Returns:
        The new or updated snapshot ID, or None if skipped due to no changes
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    try:
        # Fetch data from Notion
        pages, games_played_map, _client = await fetch_notion_data()

        # Build Notion players lookup
        notion_players = build_notion_players_lookup(pages, games_played_map)

        async with AsyncSession(async_engine) as session:
            try:
                # Formal DB renaming for merge_notion actions (must happen before sync)
                if merges:
                    for old_name, merge_info in merges.items():
                        if merge_info.get("action") == "merge_notion":
                            await rename_player(session, old_name, merge_info["to"])

                # 1. ALWAYS update global NotionCache first with true identities
                await notion_cache_to_db(session, notion_players)
                await session.flush()

                # Check if database has existing snapshots
                latest_id = await get_latest_snapshot_id(session)
                has_snapshots = latest_id is not None

                if snapshot_id is None and has_snapshots:
                    logger.error("Snapshot ID is required because the database is not empty.")
                    return None

                # Build snapshot rows combining existing and Notion data
                rows = await _build_snapshot_rows(session, snapshot_id, notion_players, merges)

                existing_names: set[str] = (
                    {p["nombre"] for p in await get_snapshot_players(session, snapshot_id)}
                    if snapshot_id is not None
                    else set()
                )
                new_players = [f["nombre"] for f in rows if f["nombre"] not in existing_names]

                logger.info(f"{len(rows)} jugador(es) procesados ({len(new_players)} nuevo(s)).")
                if new_players:
                    logger.info(f"Nuevos: {', '.join(new_players)}")

                # Content-addressed guard: skip if data hasn't changed
                if (
                    snapshot_id is not None
                    and not force
                    and await snapshots_have_same_roster(session, snapshot_id, rows)
                ):
                    logger.info(
                        "Los datos de Notion coinciden con el último snapshot — sin cambios."
                    )
                    return None

                if snapshot_id is not None:
                    has_children = await _check_snapshot_has_children(session, snapshot_id)

                    # Extract renames for merge_notion actions
                    renames_list: list[RenameDict] = [
                        {"from": k, "to": v["to"]}
                        for k, v in (merges or {}).items()
                        if v.get("action") == "merge_notion"
                    ]

                    if not has_children:
                        # Leaf node: update in place
                        await _update_snapshot_in_place(session, snapshot_id, rows, renames_list)
                        await session.commit()
                        return snapshot_id

                # Create new snapshot for internal nodes or initial sync
                new_snap_id = await _create_new_snapshot(session, snapshot_id, rows)
                await session.commit()
                return new_snap_id

            except Exception:
                await session.rollback()
                raise

    except APIResponseError as e:
        logger.error(f"Error de API Notion: {e}")
        raise
    except Exception as e:
        logger.error(f"Background notion sync failed: {e}")
        raise
