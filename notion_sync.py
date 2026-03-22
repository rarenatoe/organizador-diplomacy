"""
notion_sync.py  –  Sincroniza la base de datos de jugadores desde Notion.

Uso:
    uv run python notion_sync.py              # descarga y crea un snapshot en la DB
    uv run python notion_sync.py --dry-run    # muestra lo que se escribiría sin tocar la DB
    uv run python notion_sync.py --force      # fuerza la creación aunque los datos sean idénticos

Qué viene de Notion:
    Nombre          → propiedad 'Nombre' (title) de la DB Jugadores
    Experiencia     → 'Antiguo' si Participaciones (relation) tiene ≥1 entrada,
                       'Nuevo' si está vacía (conteo histórico total)
    Juegos_Este_Ano → partidas del año en curso: se consulta la DB Participaciones
                       filtrando por Temporada == año actual, y se cruza con los
                       IDs de la relation de cada jugador.
                       (La formula 'Nro. Partidas' siempre retorna 0 vía API —
                        limitación conocida de Notion con relations.)

Qué se preserva del último snapshot (no existe en Notion):
    prioridad        → se conserva del snapshot anterior; default 0 para jugadores nuevos
    partidas_deseadas → se conserva del snapshot anterior; default 1 para jugadores nuevos
    partidas_gm      → se conserva del snapshot anterior; default 0 para jugadores nuevos

Guard de datos idénticos:
    Si los campos de Notion (Nombre, Experiencia, Juegos_Este_Ano) coinciden
    exactamente con el último snapshot en la DB, no se crea un snapshot nuevo.
    Usa --force para forzar la creación de todos modos.

Requisitos:
    - Archivo .env con NOTION_TOKEN, NOTION_DATABASE_ID y
      NOTION_PARTICIPACIONES_DB_ID
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError
import os

import db
from utils import DIRECTORIO

# ── Player field defaults for first-time Notion players ──────────────────────

FIELD_DEFAULTS: dict[str, int] = {
    "prioridad":         0,
    "partidas_deseadas": 1,
    "partidas_gm":       0,
}

# ── Helpers de extracción ─────────────────────────────────────────────────────

def _extraer_nombre(prop: dict) -> str:
    """Extrae texto plano de una propiedad title."""
    return "".join(p.get("plain_text", "") for p in prop.get("title", [])).strip()


def _experiencia(participaciones_prop: dict) -> str:
    """'Antiguo' si el jugador tiene ≥1 participación histórica, 'Nuevo' si no."""
    return "Antiguo" if participaciones_prop.get("relation") else "Nuevo"


# ── Existing player data (from DB) ──────────────────────────────────────

def _leer_snapshot_existente(
    conn: "db.sqlite3.Connection",
) -> dict[str, dict]:
    """Returns nombre → row dict from the latest snapshot, or {} if none."""
    latest_id = db.get_latest_snapshot_id(conn)
    if latest_id is None:
        return {}
    return {
        r["nombre"]: r
        for r in db.get_snapshot_players(conn, latest_id)
    }


# ── Partidas del año actual ──────────────────────────────────────────────────

def _conteo_partidas_este_ano(
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
    db_info = client.databases.retrieve(database_id=participaciones_db_id)
    data_sources = db_info.get("data_sources", [])
    if not data_sources:
        raise RuntimeError(
            f"La DB de Participaciones '{participaciones_db_id}' no tiene data_sources. "
            "Asegúrate de que la integración tenga acceso de lectura."
        )
    ds_id: str = data_sources[0]["id"]

    conteo: dict[str, int] = {}
    sin_temporada = 0
    cursor: str | None = None

    while True:
        kwargs: dict = {"data_source_id": ds_id, "result_type": "page"}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = client.data_sources.query(**kwargs)

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
        print(
            f"  ⚠️  {sin_temporada} participación(es) sin Temporada (rollup None). "
            "Conecta la DB 'Partida' a la integración para obtener Juegos_Este_Año correcto.",
            file=sys.stderr,
        )

    return conteo


# ── Conversión Notion → filas DB ─────────────────────────────────────────────

def _paginas_a_filas(
    pages: list[dict],
    existentes: dict[str, dict],
    conteo_por_jugador: dict[str, int],
) -> list[dict]:
    """
    Merges Notion page data with existing DB snapshot data.
    Returns a list of normalized player dicts ready for DB insertion.
    Keys: Nombre, Experiencia, Juegos_Este_Ano, prioridad, partidas_deseadas, partidas_gm
    Omits pages without a name.
    """
    filas: list[dict] = []
    for page in pages:
        props = page.get("properties", {})

        # Nombre (obligatorio)
        nombre_prop = props.get("Nombre")
        if not nombre_prop:
            continue
        nombre = _extraer_nombre(nombre_prop)
        if not nombre:
            continue

        # Experiencia ← total histórico de Participaciones
        part_prop = props.get("Participaciones")
        experiencia = _experiencia(part_prop) if part_prop else "Nuevo"

        # Juegos_Este_Ano ← conteo filtrado por año (indexado por page ID del jugador)
        player_id = page["id"].replace("-", "")
        juegos = conteo_por_jugador.get(player_id, 0)

        # Preserve local fields from the latest snapshot, or use defaults
        existente = existentes.get(nombre, {})
        filas.append({
            "Nombre":            nombre,
            "Experiencia":       experiencia,
            "Juegos_Este_Ano":   juegos,
            "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
            "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
            "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
        })
    return filas


# ── Descarga desde Notion ─────────────────────────────────────────────────────

def _descargar_todos(client: Client, database_id: str) -> list[dict]:
    """
    Descarga todas las páginas de la DB paginando automáticamente.

    notion-client ≥2.7 eliminó databases.query(); hay que obtener el
    data_source_id desde databases.retrieve() y luego usar data_sources.query().
    """
    db_info = client.databases.retrieve(database_id=database_id)
    data_sources = db_info.get("data_sources", [])
    if not data_sources:
        raise RuntimeError(
            f"La base de datos '{database_id}' no tiene data_sources. "
            "Asegúrate de que la integración tenga acceso de lectura."
        )
    data_source_id: str = data_sources[0]["id"]

    pages: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs: dict = {"data_source_id": data_source_id, "result_type": "page"}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = client.data_sources.query(**kwargs)
        pages.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return pages


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga jugadores desde Notion y crea un snapshot en la DB"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra el resultado sin escribir en la DB")
    parser.add_argument("--force", action="store_true",
                        help="Crea un snapshot aunque los datos sean idénticos al último")
    args = parser.parse_args()

    load_dotenv()
    token      = os.getenv("NOTION_TOKEN")
    db_id      = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or token.startswith("secret_XXX"):
        print("❌  NOTION_TOKEN no configurado. Copia .env.example → .env y rellénalo.")
        sys.exit(1)
    if not db_id or "XXX" in db_id:
        print("❌  NOTION_DATABASE_ID no configurado. Copia .env.example → .env y rellénalo.")
        sys.exit(1)
    if not part_db_id or "XXX" in part_db_id:
        print("❌  NOTION_PARTICIPACIONES_DB_ID no configurado. Copia .env.example → .env y rellénalo.")
        sys.exit(1)

    año_actual = datetime.now().year
    client = Client(auth=token)

    print("⟳  Conectando a Notion...", end=" ", flush=True)
    try:
        pages = _descargar_todos(client, db_id)
        conteo_por_jugador = _conteo_partidas_este_ano(client, part_db_id, año_actual)
    except APIResponseError as e:
        print(f"\n❌  Error de API Notion: {e}")
        sys.exit(1)
    print(f"{len(pages)} jugador(es), {sum(conteo_por_jugador.values())} partida(s) en {año_actual}.")

    conn = db.get_db()
    existentes = _leer_snapshot_existente(conn)
    filas = _paginas_a_filas(pages, existentes, conteo_por_jugador)

    nuevos = [f["Nombre"] for f in filas if f["Nombre"] not in existentes]
    print(f"⟳  {len(filas)} jugador(es) procesados ({len(nuevos)} nuevo(s)).")
    if nuevos:
        print(f"   Nuevos: {', '.join(nuevos)}")

    if args.dry_run:
        print("\n── dry-run: snapshot que se crearía ──")
        for fila in filas:
            print(f"  {fila['Nombre']} | {fila['Experiencia']} | {fila['Juegos_Este_Ano']}")
        print("\n(No se escribió nada en la DB)")
        conn.close()
        return

    # ── Content-addressed guard: skip if data hasn't changed ──────────────────
    latest_id = db.get_latest_snapshot_id(conn)
    if latest_id is not None and not args.force:
        if db.snapshots_have_same_roster(conn, latest_id, filas):
            print("✓  Los datos de Notion coinciden con el último snapshot — sin cambios.")
            print("   Usa --force para crear un snapshot igualmente.")
            conn.close()
            return

    # ── Persist new snapshot atomically ───────────────────────────────────────
    try:
        snap_id = db.create_snapshot(conn, "notion_sync")
        for fila in filas:
            pid = db.get_or_create_player(conn, fila["Nombre"])
            db.add_snapshot_player(
                conn, snap_id, pid,
                fila["Experiencia"],
                fila["Juegos_Este_Ano"],
                fila["prioridad"],
                fila["partidas_deseadas"],
                fila["partidas_gm"],
            )
        db.create_sync_event(conn, latest_id, snap_id)
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()
    print(f"✓  Snapshot #{snap_id} creado con {len(filas)} jugador(es).")
    if latest_id:
        print(f"   sync_event: snapshot #{latest_id} → #{snap_id}")
    else:
        print("   (primer sync — sin snapshot anterior)")


if __name__ == "__main__":
    main()
