"""
cache_daemon.py – Background process for periodic Notion data caching.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
import concurrent.futures
from datetime import datetime

from notion_client import Client
from dotenv import load_dotenv

from backend.db import db
from backend.sync.notion_sync import (
    descargar_todos,
    conteo_partidas_este_ano,
    _extraer_nombre,
    _experiencia,
    _normalize_name,
    _extraer_numero,
    COUNTRY_PROPS
)

def update_notion_cache(
    conn: sqlite3.Connection,
    client: Client,
    db_id: str,
    part_db_id: str
) -> None:
    """
    Fetches all player data from Notion and updates the local notion_cache table.
    """
    año_actual = datetime.now().year
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_pages = executor.submit(descargar_todos, client, db_id)
        future_conteo = executor.submit(conteo_partidas_este_ano, client, part_db_id, año_actual)
        
        pages = future_pages.result()
        conteo_por_jugador = future_conteo.result()

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for page in pages:
        props = page.get("properties", {})
        nombre_prop = props.get("Nombre")
        if not nombre_prop:
            continue
        nombre = _extraer_nombre(nombre_prop)
        if not nombre:
            continue
            
        part_prop = props.get("Participaciones")
        experiencia = _experiencia(part_prop) if part_prop else "Nuevo"
        
        player_id = page["id"].replace("-", "")
        juegos = conteo_por_jugador.get(player_id, 0)
        
        countries_data = {
            key: _extraer_numero(props.get(notion_name, {}))
            for key, notion_name in COUNTRY_PROPS.items()
        }
        
        conn.execute(
            """
            INSERT OR REPLACE INTO notion_cache
            (notion_id, nombre, experiencia, juegos_este_ano, 
             c_england, c_france, c_germany, c_italy, 
             c_austria, c_russia, c_turkey, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page["id"],
                nombre,
                experiencia,
                juegos,
                countries_data["c_england"],
                countries_data["c_france"],
                countries_data["c_germany"],
                countries_data["c_italy"],
                countries_data["c_austria"],
                countries_data["c_russia"],
                countries_data["c_turkey"],
                last_updated
            )
        )
    conn.commit()


def _run_sync_loop() -> None:
    """Infinite loop for the background thread."""
    load_dotenv()
    token      = os.getenv("NOTION_TOKEN")
    db_id      = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not all([token, db_id, part_db_id]) or token.startswith("secret_XXX"):
        print(" [Cache Daemon] Skipping background sync: Missing Notion credentials.")
        return

    client = Client(auth=token)
    
    while True:
        print(f" [Cache Daemon] Starting sync at {datetime.now()}")
        conn = db.get_db()
        try:
            update_notion_cache(conn, client, db_id, part_db_id)
            print(f" [Cache Daemon] Sync complete. Sleeping for 15 minutes.")
        except Exception as e:
            print(f" [Cache Daemon] Error during sync: {e}")
        finally:
            conn.close()
            
        time.sleep(900) # 15 minutes


def start_background_sync() -> None:
    """Starts the background daemon thread."""
    thread = threading.Thread(target=_run_sync_loop, daemon=True)
    thread.start()
