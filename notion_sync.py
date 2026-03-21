"""
notion_sync.py  –  Sincroniza la base de datos de jugadores desde Notion.

Uso:
    uv run python notion_sync.py              # descarga y fusiona con jugadores.csv
    uv run python notion_sync.py --dry-run    # muestra lo que se escribiría sin tocar el CSV

Qué viene de Notion:
    Nombre          → propiedad 'Nombre' (title)
    Juegos_Este_Ano → propiedad 'Nro. Partidas' (formula numérica)
    Experiencia     → derivado de 'Participaciones' (relation):
                        vacío  → "Nuevo"
                        con entradas → "Antiguo"

Qué se preserva del jugadores.csv existente (no existe en Notion):
    Prioridad        → se conserva del CSV; default "False" para jugadores nuevos
    Partidas_Deseadas → se conserva del CSV; default "1" para jugadores nuevos
    Partidas_GM      → se conserva del CSV; default "0" para jugadores nuevos

Requisitos:
    - Archivo .env en la raíz del proyecto con NOTION_TOKEN y NOTION_DATABASE_ID
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError
import os

# ── Configuración ─────────────────────────────────────────────────────────────

CSV_PATH: Path = Path(__file__).parent / "jugadores.csv"

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


def _desde_participaciones(prop: dict) -> tuple[str, str]:
    """
    A partir de la relation 'Participaciones' devuelve (Experiencia, Juegos_Este_Ano).
    - Experiencia: 'Antiguo' si tiene ≥1 entrada, 'Nuevo' si está vacía.
    - Juegos_Este_Ano: cantidad de entradas en la relation (como string).
    Nota: la formula 'Nro. Partidas' siempre devuelve 0 vía API (limitación de
    Notion), por lo que usamos directamente el conteo de la relation.
    """
    entradas = prop.get("relation", [])
    count = len(entradas)
    return ("Antiguo" if count > 0 else "Nuevo"), str(count)


# ── CSV existente ─────────────────────────────────────────────────────────────

def _leer_csv_existente(ruta: Path) -> dict[str, dict[str, str]]:
    """Lee jugadores.csv y retorna un dict nombre → fila completa."""
    if not ruta.exists():
        return {}
    with ruta.open(encoding="utf-8") as f:
        return {row["Nombre"]: row for row in csv.DictReader(f)}


# ── Conversión Notion → filas CSV ─────────────────────────────────────────────

def _paginas_a_filas(
    pages: list[dict],
    existentes: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    """
    Convierte páginas de Notion en filas listas para jugadores.csv.
    Nombre, Juegos_Este_Ano y Experiencia vienen de Notion.
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

        # Experiencia y Juegos_Este_Ano ← 'Participaciones' (relation)
        # (La formula 'Nro. Partidas' siempre retorna 0 vía API)
        part_prop = props.get("Participaciones")
        experiencia, juegos = _desde_participaciones(part_prop) if part_prop else ("Nuevo", "0")

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

def _escribir_csv(filas: list[dict[str, str]], ruta: Path) -> None:
    with ruta.open(mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(filas)


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

    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")

    if not token or token.startswith("secret_XXX"):
        print("❌  NOTION_TOKEN no configurado. Copia .env.example → .env y rellénalo.")
        sys.exit(1)
    if not db_id or "XXX" in db_id:
        print("❌  NOTION_DATABASE_ID no configurado. Copia .env.example → .env y rellénalo.")
        sys.exit(1)

    client = Client(auth=token)

    print("⟳  Conectando a Notion...", end=" ", flush=True)
    try:
        pages = _descargar_todos(client, db_id)
    except APIResponseError as e:
        print(f"\n❌  Error de API Notion: {e}")
        sys.exit(1)
    print(f"{len(pages)} página(s) recibidas.")

    existentes = _leer_csv_existente(CSV_PATH)
    filas = _paginas_a_filas(pages, existentes)

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
        _escribir_csv(filas, CSV_PATH)
        print(f"✓  {CSV_PATH.name} actualizado con {len(filas)} jugador(es).")


if __name__ == "__main__":
    main()
