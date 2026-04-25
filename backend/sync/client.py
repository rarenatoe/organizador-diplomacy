import asyncio
import concurrent.futures
import logging
import os
from datetime import datetime
from typing import Any, TypedDict, cast

from dotenv import load_dotenv
from notion_client import Client

logger = logging.getLogger(__name__)


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


COUNTRY_PROPS: dict[str, str] = {
    "c_england": "∀ 🇬🇧",
    "c_france": "∀ 🇫🇷",
    "c_germany": "∀ 🇩🇪",
    "c_italy": "∀ 🇮🇹",
    "c_austria": "∀ 🇦🇹",
    "c_russia": "∀ 🇷🇺",
    "c_turkey": "∀ 🇹🇷",
}


def extract_number(prop: NotionProperty | None) -> int:
    if not prop:
        return 0
    if prop.get("type") == "number":
        return int(prop.get("number") or 0)
    if prop.get("type") == "formula":
        return int(prop.get("formula", {}).get("number") or 0)
    return 0


def extract_name(prop: NotionProperty | None) -> str:
    if not prop:
        return ""
    return "".join(p.get("plain_text", "") for p in prop.get("title", [])).strip()


def calculate_experience(participaciones_prop: NotionProperty | None) -> bool:
    if not participaciones_prop:
        return True
    return not bool(participaciones_prop.get("relation"))


def download_all_pages(client: Client, database_id: str) -> list[NotionPage]:
    db_info = cast("dict[str, Any]", client.databases.retrieve(database_id=database_id))
    data_sources = db_info.get("data_sources", [])
    if not data_sources:
        raise RuntimeError("La base de datos no tiene data_sources.")

    data_source_id: str = data_sources[0]["id"]
    prop_ids: list[str] = []
    props = db_info.get("properties", {})
    required_names = ["Nombre", "Participaciones", "Alias"] + list(COUNTRY_PROPS.values())

    for name in required_names:
        if name in props:
            prop_ids.append(props[name]["id"])

    pages: list[NotionPage] = []
    cursor: str | None = None

    while True:
        kwargs: dict[str, Any] = {"data_source_id": data_source_id, "result_type": "page"}
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


def count_games_this_year(client: Client, participaciones_db_id: str, año: int) -> dict[str, int]:
    db_info = cast("dict[str, Any]", client.databases.retrieve(database_id=participaciones_db_id))
    data_sources = db_info.get("data_sources", [])
    if not data_sources:
        raise RuntimeError("La DB de Participaciones no tiene data_sources.")

    ds_id: str = data_sources[0]["id"]
    prop_ids: list[str] = []
    props = db_info.get("properties", {})
    for name in ["Temporada", "Jugador"]:
        if name in props:
            prop_ids.append(props[name]["id"])

    conteo: dict[str, int] = {}
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

        response = cast("dict[str, Any]", client.data_sources.query(**kwargs))

        for page in response.get("results", []):
            props = page.get("properties", {})
            temporada = props.get("Temporada", {}).get("rollup", {}).get("number")
            if temporada is None or int(temporada) != año:
                continue

            for rel in props.get("Jugador", {}).get("relation", []):
                pid = rel["id"].replace("-", "")
                conteo[pid] = conteo.get(pid, 0) + 1

        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return conteo


async def fetch_notion_data() -> tuple[list[NotionPage], dict[str, int], Client]:
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

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_pages = executor.submit(download_all_pages, client, db_id)
        future_conteo = executor.submit(count_games_this_year, client, part_db_id, año_actual)

        pages = await loop.run_in_executor(None, future_pages.result)
        games_played_map = await loop.run_in_executor(None, future_conteo.result)

    return pages, games_played_map, client
