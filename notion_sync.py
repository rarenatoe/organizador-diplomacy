"""
notion_sync.py  –  Sincroniza la base de datos de jugadores desde Notion.

Uso:
    uv run python notion_sync.py              # descarga y fusiona con jugadores.csv
    uv run python notion_sync.py --dry-run    # muestra lo que se escribiría sin tocar el CSV

Qué viene de Notion:
    Nombre          → propiedad 'Nombre' (title) de la DB Jugadores
    Experiencia     → 'Antiguo' si Participaciones (relation) tiene ≥1 entrada,
                       'Nuevo' si está vacía (conteo histórico total)
    Juegos_Este_Ano → partidas del año en curso: se consulta la DB Participaciones
                       filtrando por Temporada == año actual, y se cruza con los
                       IDs de la relation de cada jugador.
                       (La formula 'Nro. Partidas' siempre retorna 0 vía API —
                        limitación conocida de Notion con relations.)

Qué se preserva del jugadores.csv existente (no existe en Notion):
    Prioridad        → se conserva del CSV; default "False" para jugadores nuevos
    Partidas_Deseadas → se conserva del CSV; default "1" para jugadores nuevos
    Partidas_GM      → se conserva del CSV; default "0" para jugadores nuevos

Requisitos:
    - Archivo .env con NOTION_TOKEN, NOTION_DATABASE_ID y
      NOTION_PARTICIPACIONES_DB_ID
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError
import os

from utils import DIRECTORIO, siguiente_csv, ultimo_csv

# ── Configuración ──────────────────────────────────────────────────

CSV_FIELDNAMES: list[str] = [
    "Nombre", "Experiencia", "Juegos_Este_Ano",
    "Prioridad", "Partidas_Deseadas", "Partidas_GM",
]

# Valores por defecto para jugadores que no están aún en jugadores.csv
CSV_DEFAULTS: dict[str, str] = {
    "Prioridad":         "False",
    "Partidas_Deseadas": "1",
    "Partidas_GM":       "0",
}

# ── Helpers de extracción ─────────────────────────────────────────────────────

def _extraer_nombre(prop: dict) -> str:
    """Extrae texto plano de una propiedad title."""
    return "".join(p.get("plain_text", "") for p in prop.get("title", [])).strip()


def _experiencia(participaciones_prop: dict) -> str:
    """'Antiguo' si el jugador tiene ≥1 participación histórica, 'Nuevo' si no."""
    return "Antiguo" if participaciones_prop.get("relation") else "Nuevo"


# ── CSV existente ─────────────────────────────────────────────────────────────

def _leer_csv_existente() -> dict[str, dict[str, str]]:
    """Lee el último jugadores_NNNN.csv y retorna un dict nombre → fila completa."""
    ruta = ultimo_csv()
    if ruta is None:
        return {}
    with ruta.open(encoding="utf-8") as f:
        return {row["Nombre"]: row for row in csv.DictReader(f)}


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


# ── Conversión Notion → filas CSV ─────────────────────────────────────────────

def _paginas_a_filas(
    pages: list[dict],
    existentes: dict[str, dict[str, str]],
    conteo_por_jugador: dict[str, int],
) -> list[dict[str, str]]:
    """
    Convierte páginas de Notion en filas listas para jugadores.csv.
    Nombre, Experiencia y Juegos_Este_Ano vienen de Notion.
    Prioridad, Partidas_Deseadas y Partidas_GM se preservan del CSV existente
    (o se usan defaults para jugadores que aún no están en el CSV).
    Omite páginas sin nombre.
    """
    filas: list[dict[str, str]] = []
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
        juegos = str(conteo_por_jugador.get(player_id, 0))

        # Columnas que vienen del CSV local (preservar o usar defaults)
        existente = existentes.get(nombre, {})
        filas.append({
            "Nombre":            nombre,
            "Experiencia":       experiencia,
            "Juegos_Este_Ano":   juegos,
            "Prioridad":         existente.get("Prioridad",         CSV_DEFAULTS["Prioridad"]),
            "Partidas_Deseadas": existente.get("Partidas_Deseadas", CSV_DEFAULTS["Partidas_Deseadas"]),
            "Partidas_GM":       existente.get("Partidas_GM",       CSV_DEFAULTS["Partidas_GM"]),
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


# ── Escritura CSV ─────────────────────────────────────────────────────────────

def _escribir_csv(filas: list[dict[str, str]]) -> Path:
    ruta = siguiente_csv()
    with ruta.open(mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(filas)
    return ruta


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga jugadores desde Notion y fusiona con jugadores.csv"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el resultado sin escribir el CSV",
    )
    args = parser.parse_args()

    load_dotenv()

    token        = os.getenv("NOTION_TOKEN")
    db_id        = os.getenv("NOTION_DATABASE_ID")
    part_db_id   = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

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

    existentes = _leer_csv_existente()
    filas = _paginas_a_filas(pages, existentes, conteo_por_jugador)

    nuevos = [f["Nombre"] for f in filas if f["Nombre"] not in existentes]
    print(f"⟳  {len(filas)} jugador(es) procesados ({len(nuevos)} nuevo(s)).")
    if nuevos:
        print(f"   Nuevos: {', '.join(nuevos)}")

    if args.dry_run:
        print("\n── dry-run: contenido que se escribiría ──")
        writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(filas)
        print("\n(No se escribió ningún archivo)")
    else:
        ruta = _escribir_csv(filas)
        print(f"✓  {ruta.name} creado con {len(filas)} jugador(es).")


if __name__ == "__main__":
    main()
