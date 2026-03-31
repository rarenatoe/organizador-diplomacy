"""
cache_daemon.py – Async background process for periodic Notion data caching.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
from datetime import datetime
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from notion_client import Client
from sqlalchemy import select

from backend.db.connection import async_engine
from backend.db.models import NotionCache
from backend.sync.notion_sync import (
    COUNTRY_PROPS,
    conteo_partidas_este_ano,
    descargar_todos,
    experiencia,
    extraer_nombre,
    extraer_numero,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def update_notion_cache(
    session: AsyncSession, client: Client, db_id: str, part_db_id: str
) -> None:
    """
    Async version that uses AsyncSession.
    Fetches all player data from Notion and updates the local notion_cache table.
    """
    año_actual = datetime.now().year

    # Run Notion API calls in thread pool (they are blocking I/O)
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_pages = executor.submit(descargar_todos, client, db_id)
        future_conteo = executor.submit(conteo_partidas_este_ano, client, part_db_id, año_actual)

        pages = await loop.run_in_executor(None, future_pages.result)
        conteo_por_jugador = await loop.run_in_executor(None, future_conteo.result)

    last_updated = datetime.now()

    for page in pages:
        props = page.get("properties", {})
        nombre_prop = props.get("Nombre")
        if not nombre_prop:
            continue
        nombre = extraer_nombre(nombre_prop)
        if not nombre:
            continue

        part_prop = props.get("Participaciones")
        experiencia_val = experiencia(part_prop) if part_prop else "Nuevo"

        player_id = page["id"].replace("-", "")
        juegos = conteo_por_jugador.get(player_id, 0)

        countries_data = {
            key: extraer_numero(props.get(notion_name, {}))
            for key, notion_name in COUNTRY_PROPS.items()
        }

        # Check if cache entry exists
        result = await session.execute(
            select(NotionCache).where(NotionCache.notion_id == page["id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.nombre = nombre
            existing.experiencia = experiencia_val
            existing.juegos_este_ano = juegos
            existing.c_england = countries_data["c_england"]
            existing.c_france = countries_data["c_france"]
            existing.c_germany = countries_data["c_germany"]
            existing.c_italy = countries_data["c_italy"]
            existing.c_austria = countries_data["c_austria"]
            existing.c_russia = countries_data["c_russia"]
            existing.c_turkey = countries_data["c_turkey"]
            existing.last_updated = last_updated
        else:
            # Create new
            cache_entry = NotionCache(
                notion_id=page["id"],
                nombre=nombre,
                experiencia=experiencia_val,
                juegos_este_ano=juegos,
                c_england=countries_data["c_england"],
                c_france=countries_data["c_france"],
                c_germany=countries_data["c_germany"],
                c_italy=countries_data["c_italy"],
                c_austria=countries_data["c_austria"],
                c_russia=countries_data["c_russia"],
                c_turkey=countries_data["c_turkey"],
                last_updated=last_updated,
            )
            session.add(cache_entry)


async def daemon_loop() -> None:
    """
    Async daemon loop that runs indefinitely with asyncio.sleep.
    """
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not all([token, db_id, part_db_id]) or not token or token.startswith("secret_XXX"):
        print(" [Cache Daemon] Skipping background sync: Missing Notion credentials.")
        return

    # Type assertions for mypy/pyright
    assert db_id is not None
    assert part_db_id is not None

    client = Client(auth=token)
    from sqlalchemy.ext.asyncio.session import AsyncSession

    while True:
        print(f" [Cache Daemon] Starting sync at {datetime.now()}")
        async with AsyncSession(async_engine) as session:
            try:
                await update_notion_cache(session, client, db_id, part_db_id)
                await session.commit()
                print(" [Cache Daemon] Sync complete. Sleeping for 15 minutes.")
            except Exception as e:
                await session.rollback()
                print(f" [Cache Daemon] Error during sync: {e}")
            finally:
                await session.close()

        await asyncio.sleep(900)  # 15 minutes


async def start_background_sync() -> None:
    """Starts the async background daemon."""
    asyncio.create_task(daemon_loop())
