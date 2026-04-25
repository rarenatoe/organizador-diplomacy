# backend/sync/core.py
import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from dotenv import load_dotenv
from notion_client.errors import APIResponseError

from backend.api.models.snapshots import HistoryState, RenameChange
from backend.crud.chain import create_branch_edge
from backend.crud.players import get_or_create_player, rename_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    create_snapshot,
    generate_deep_diff,
    get_latest_snapshot_id,
    get_snapshot_players,
    log_snapshot_history,
    snapshots_have_same_roster,
    update_notion_cache,
)
from backend.db.connection import async_engine
from backend.db.models import SnapshotSource

from .client import (
    COUNTRY_PROPS,
    NotionPage,
    calculate_experience,
    extract_name,
    extract_number,
    fetch_notion_data,
)
from .matching import normalize_name

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


SyncStateStatus = Literal["pending", "syncing", "ready", "unconfigured", "error"]


class SyncState:
    status: SyncStateStatus = "pending"


class NotionPlayerDict(TypedDict):
    notion_id: str
    nombre: str
    is_new: bool
    juegos_este_ano: int
    alias: list[str]
    c_england: int
    c_france: int
    c_germany: int
    c_italy: int
    c_austria: int
    c_russia: int
    c_turkey: int


FIELD_DEFAULTS: dict[str, int] = {
    "has_priority": False,
    "partidas_deseadas": 1,
    "partidas_gm": 0,
}


def build_notion_players_lookup(
    pages: list[NotionPage],
    games_played_map: dict[str, int],
) -> dict[str, NotionPlayerDict]:
    notion_players: dict[str, NotionPlayerDict] = {}
    for page in pages:
        props = page.get("properties", {})
        nombre_prop = props.get("Nombre")
        if not nombre_prop:
            continue
        nombre = extract_name(nombre_prop)
        if not nombre:
            continue

        experience_val = calculate_experience(props.get("Participaciones"))
        player_id = page["id"].replace("-", "")
        games_count = games_played_map.get(player_id, 0)

        alias_prop = props.get("Alias")
        alias_text = (
            "".join(p.get("plain_text", "") for p in alias_prop.get("rich_text", []))
            if alias_prop
            else ""
        )
        alias_list = [a.strip() for a in alias_text.split(",") if a.strip()]

        countries_data = {
            key: extract_number(props.get(notion_name))
            for key, notion_name in COUNTRY_PROPS.items()
        }

        notion_players[normalize_name(nombre)] = NotionPlayerDict(
            {
                "notion_id": page["id"],
                "nombre": nombre,
                "is_new": experience_val,
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


def find_notion_player(
    name: str, notion_players: dict[str, NotionPlayerDict]
) -> NotionPlayerDict | None:
    norm_name = normalize_name(name)
    if norm_name in notion_players:
        return notion_players[norm_name]
    for p in notion_players.values():
        if norm_name in p.get("alias", []):
            return p
    return None


async def _check_snapshot_has_children(session: "AsyncSession", snapshot_id: int) -> bool:
    from sqlalchemy import select

    from backend.db.models import TimelineEdge

    result = await session.execute(
        select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snapshot_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _update_snapshot_in_place(
    session: "AsyncSession",
    snapshot_id: int,
    rows: list[dict[str, Any]],
    renames: list[RenameChange],
) -> None:
    from sqlalchemy import delete, select, update

    from backend.db.models import Player, Snapshot, SnapshotPlayer

    previous_players = await get_snapshot_players(session, snapshot_id)

    for r in renames or []:
        target_exists = await session.execute(select(Player).where(Player.name == r.new_name))
        if not target_exists.scalar_one_or_none():
            await session.execute(
                update(Player).where(Player.name == r.old_name).values(name=r.new_name)
            )

    await session.execute(
        update(Snapshot).where(Snapshot.id == snapshot_id).values(source="notion_sync")
    )
    await session.execute(delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id))

    for row in rows:
        pid = await get_or_create_player(session, row["nombre"], row.get("notion_id"))
        await add_player_to_snapshot(
            session,
            snapshot_id,
            pid,
            row["juegos_este_ano"],
            row["partidas_deseadas"],
            row["partidas_gm"],
            has_priority=row["has_priority"],
            is_new=row["is_new"],
        )

    roster_fields = {
        "nombre",
        "is_new",
        "juegos_este_ano",
        "has_priority",
        "partidas_deseadas",
        "partidas_gm",
    }
    prev_roster = [p.model_dump(include=roster_fields) for p in previous_players]
    new_roster = [
        {
            "nombre": r["nombre"],
            "is_new": r["is_new"],
            "juegos_este_ano": r["juegos_este_ano"],
            "has_priority": r.get("has_priority", False),
            "partidas_deseadas": r.get("partidas_deseadas", 1),
            "partidas_gm": r.get("partidas_gm", 0),
        }
        for r in rows
    ]

    diff = generate_deep_diff(prev_roster, new_roster, renames)
    await log_snapshot_history(
        session,
        snapshot_id=snapshot_id,
        action_type=SnapshotSource.NOTION_SYNC,
        changes=diff,
        previous_state=HistoryState(players=previous_players),
    )


async def _create_new_snapshot(
    session: "AsyncSession", source_snapshot_id: int | None, rows: list[dict[str, Any]]
) -> int:
    snap_id = await create_snapshot(session, SnapshotSource.NOTION_SYNC)
    for row in rows:
        pid = await get_or_create_player(session, row["nombre"], row.get("notion_id"))
        await add_player_to_snapshot(
            session,
            snap_id,
            pid,
            row["juegos_este_ano"],
            row["partidas_deseadas"],
            row["partidas_gm"],
            has_priority=row["has_priority"],
            is_new=row["is_new"],
        )

    if source_snapshot_id is not None:
        await create_branch_edge(session, source_snapshot_id, snap_id)
    return snap_id


async def _build_snapshot_rows(
    session: "AsyncSession",
    source_snapshot_id: int | None,
    notion_players: dict[str, NotionPlayerDict],
    merges: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    merges = merges or {}

    if source_snapshot_id is not None:
        existing_list = await get_snapshot_players(session, source_snapshot_id)
        existing_map = {p.nombre: p for p in existing_list}
        merged_notion_normalized = {normalize_name(v["to"]) for v in merges.values()}
        reverse_merges = {v["to"]: {"from": k, **v} for k, v in merges.items()}

        for nombre, existente in existing_map.items():
            if nombre in merges:
                merge_info = merges[nombre]
                notion_norm = normalize_name(merge_info["to"])
                if notion_norm in notion_players:
                    notion_data = notion_players[notion_norm]
                    rows.append(
                        {
                            "nombre": notion_data["nombre"]
                            if merge_info["action"] == "merge_notion"
                            else nombre,
                            "is_new": notion_data["is_new"],
                            "juegos_este_ano": notion_data["juegos_este_ano"],
                            "has_priority": existente.has_priority,
                            "partidas_deseadas": existente.partidas_deseadas,
                            "partidas_gm": existente.partidas_gm,
                            "alias": notion_data.get("alias", []),
                            "notion_id": notion_data["notion_id"],
                            **{c: notion_data[c] for c in COUNTRY_PROPS},
                        }
                    )
                    continue

            if nombre in reverse_merges:
                notion_norm = normalize_name(nombre)
                if notion_norm in notion_players:
                    notion_data = notion_players[notion_norm]
                    rows.append(
                        {
                            "nombre": notion_data["nombre"],
                            "is_new": notion_data["is_new"],
                            "juegos_este_ano": notion_data["juegos_este_ano"],
                            "has_priority": existente.has_priority,
                            "partidas_deseadas": existente.partidas_deseadas,
                            "partidas_gm": existente.partidas_gm,
                            "alias": notion_data.get("alias", []),
                            "notion_id": notion_data["notion_id"],
                            **{c: notion_data[c] for c in COUNTRY_PROPS},
                        }
                    )
                    continue

            notion_data = find_notion_player(nombre, notion_players)
            if (
                notion_data
                and normalize_name(notion_data["nombre"]) not in merged_notion_normalized
            ):
                rows.append(
                    {
                        "nombre": nombre,
                        "is_new": notion_data["is_new"],
                        "juegos_este_ano": notion_data["juegos_este_ano"],
                        "has_priority": existente.has_priority,
                        "partidas_deseadas": existente.partidas_deseadas,
                        "partidas_gm": existente.partidas_gm,
                        "alias": notion_data.get("alias", []),
                        "notion_id": notion_data["notion_id"],
                        **{c: notion_data[c] for c in COUNTRY_PROPS},
                    }
                )
            else:
                rows.append(
                    {
                        "nombre": nombre,
                        "is_new": existente.is_new,
                        "juegos_este_ano": existente.juegos_este_ano,
                        "has_priority": existente.has_priority,
                        "partidas_deseadas": existente.partidas_deseadas,
                        "partidas_gm": existente.partidas_gm,
                        **{c: getattr(existente, c, 0) for c in COUNTRY_PROPS},
                    }
                )
    else:
        for _, notion_data in notion_players.items():
            rows.append(
                {
                    "nombre": notion_data["nombre"],
                    "is_new": notion_data["is_new"],
                    "juegos_este_ano": notion_data["juegos_este_ano"],
                    "has_priority": FIELD_DEFAULTS["has_priority"],
                    "partidas_deseadas": FIELD_DEFAULTS["partidas_deseadas"],
                    "partidas_gm": FIELD_DEFAULTS["partidas_gm"],
                    "alias": notion_data.get("alias", []),
                    "notion_id": notion_data["notion_id"],
                    **{c: notion_data[c] for c in COUNTRY_PROPS},
                }
            )

    return rows


async def notion_cache_to_db(
    session: "AsyncSession", notion_players: dict[str, NotionPlayerDict]
) -> None:
    cache_rows: list[dict[str, Any]] = []
    for nd in notion_players.values():
        cache_rows.append(
            {
                "notion_id": nd["notion_id"],
                "nombre": nd["nombre"],
                "is_new": nd["is_new"],
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


async def daemon_loop() -> None:
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    if not token or token.startswith("secret_XXX"):
        SyncState.status = "unconfigured"
        return
    SyncState.status = "syncing"
    while True:
        try:
            pages, games_played_map, _client = await fetch_notion_data()
            notion_players = build_notion_players_lookup(pages, games_played_map)
            from sqlalchemy.ext.asyncio.session import AsyncSession

            async with AsyncSession(async_engine) as session:
                await notion_cache_to_db(session, notion_players)
                await session.commit()
            SyncState.status = "ready"
        except Exception:
            SyncState.status = "error"
        await asyncio.sleep(900)


async def start_background_sync() -> None:
    asyncio.create_task(daemon_loop())


async def run_notion_sync_background(
    snapshot_id: int | None = None,
    *,
    force: bool = False,
    merges: dict[str, dict[str, str]] | None = None,
) -> int | None:
    from sqlalchemy.ext.asyncio import AsyncSession

    try:
        pages, games_played_map, _client = await fetch_notion_data()
        notion_players = build_notion_players_lookup(pages, games_played_map)

        async with AsyncSession(async_engine) as session:
            try:
                if merges:
                    for old_name, merge_info in merges.items():
                        if merge_info.get("action") == "merge_notion":
                            await rename_player(session, old_name, merge_info["to"])

                await notion_cache_to_db(session, notion_players)
                await session.flush()

                latest_id = await get_latest_snapshot_id(session)
                if snapshot_id is None and latest_id is not None:
                    return None

                rows = await _build_snapshot_rows(session, snapshot_id, notion_players, merges)

                if (
                    snapshot_id is not None
                    and not force
                    and await snapshots_have_same_roster(session, snapshot_id, rows)
                ):
                    return None

                if snapshot_id is not None:
                    has_children = await _check_snapshot_has_children(session, snapshot_id)
                    renames_list = [
                        RenameChange(old_name=k, new_name=v["to"])
                        for k, v in (merges or {}).items()
                        if v.get("action") == "merge_notion"
                    ]

                    if not has_children:
                        await _update_snapshot_in_place(session, snapshot_id, rows, renames_list)
                        await session.commit()
                        return snapshot_id

                new_snap_id = await _create_new_snapshot(session, snapshot_id, rows)
                await session.commit()
                return new_snap_id

            except Exception:
                await session.rollback()
                raise
    except APIResponseError:
        raise
    except Exception:
        raise
