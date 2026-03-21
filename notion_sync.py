"""
notion_sync.py  –  Sincroniza la base de datos de jugadores desde Notion.

Uso:
    uv run python notion_sync.py              # descarga y sobreescribe jugadores.csv
    uv run python notion_sync.py --dry-run    # muestra lo que se escribiría sin tocar el CSV

Requisitos:
    - Archivo .env en la raíz del proyecto con NOTION_TOKEN y NOTION_DATABASE_ID
    - La base de datos de Notion debe tener exactamente las columnas definidas en
      COLUMN_MAP (los nombres son case-sensitive; ajusta si los tuyos difieren).

Flujo:
    Notion DB → lista de Jugador Python → jugadores.csv
    (una sola dirección; nunca escribe de vuelta a Notion)
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

# Mapeo: nombre de columna en Notion → nombre de columna en el CSV.
# Ajusta los valores de la izquierda si tus propiedades en Notion tienen
# nombres distintos.
COLUMN_MAP: dict[str, str] = {
    "Nombre":            "Nombre",
    "Experiencia":       "Experiencia",       # "Nuevo" o "Antiguo"
    "Juegos_Este_Ano":   "Juegos_Este_Ano",   # número entero
    "Prioridad":         "Prioridad",         # checkbox → "True"/"False"
    "Partidas_Deseadas": "Partidas_Deseadas", # número entero
    "Partidas_GM":       "Partidas_GM",       # número entero
}

CSV_FIELDNAMES: list[str] = list(COLUMN_MAP.values())

# ── Helpers de extracción de propiedades Notion ───────────────────────────────

def _extraer_texto(prop: dict) -> str:
    """Extrae el texto plano de una propiedad title o rich_text."""
    tipo = prop.get("type")
    if tipo == "title":
        partes = prop.get("title", [])
    elif tipo == "rich_text":
        partes = prop.get("rich_text", [])
    else:
        return ""
    return "".join(p.get("plain_text", "") for p in partes).strip()


def _extraer_numero(prop: dict) -> str:
    """Extrae un número como string (devuelve '0' si es None)."""
    valor = prop.get("number")
    return str(int(valor)) if valor is not None else "0"


def _extraer_select(prop: dict) -> str:
    """Extrae el nombre de una propiedad select."""
    sel = prop.get("select")
    return sel["name"].strip() if sel else ""


def _extraer_checkbox(prop: dict) -> str:
    """Convierte un checkbox en 'True' o 'False'."""
    return str(prop.get("checkbox", False))


# Despacho por tipo de propiedad Notion
_EXTRACTORES: dict[str, object] = {
    "title":     _extraer_texto,
    "rich_text": _extraer_texto,
    "number":    _extraer_numero,
    "select":    _extraer_select,
    "checkbox":  _extraer_checkbox,
}


def _extraer_propiedad(prop: dict) -> str:
    """Extrae el valor de una propiedad Notion sin importar su tipo."""
    tipo = prop.get("type", "")
    extractor = _EXTRACTORES.get(tipo)
    if extractor is None:
        return ""
    return extractor(prop)  # type: ignore[operator]


# ── Lógica principal ──────────────────────────────────────────────────────────

def _paginas_a_filas(pages: list[dict]) -> list[dict[str, str]]:
    """
    Convierte una lista de páginas de Notion en filas listas para el CSV.
    Omite páginas donde 'Nombre' esté vacío (filas en blanco en la DB).
    """
    filas: list[dict[str, str]] = []
    for page in pages:
        props = page.get("properties", {})
        fila: dict[str, str] = {}
        for notion_col, csv_col in COLUMN_MAP.items():
            prop = props.get(notion_col)
            if prop is None:
                print(
                    f"  ⚠️  Columna '{notion_col}' no encontrada en la página "
                    f"'{page.get('id', '?')}'. Se usará cadena vacía.",
                    file=sys.stderr,
                )
                fila[csv_col] = ""
            else:
                fila[csv_col] = _extraer_propiedad(prop)

        if not fila.get("Nombre"):
            continue  # saltar filas sin nombre
        filas.append(fila)
    return filas


def _descargar_todos(client: Client, database_id: str) -> list[dict]:
    """Descarga todas las páginas de la DB paginando automáticamente."""
    pages: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs: dict = {"database_id": database_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = client.databases.query(**kwargs)
        pages.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return pages


def _escribir_csv(filas: list[dict[str, str]], ruta: Path) -> None:
    with ruta.open(mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(filas)


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga la DB de jugadores desde Notion y sobreescribe jugadores.csv"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el resultado sin escribir el CSV",
    )
    args = parser.parse_args()

    # Cargar .env (si existe; en CI las variables ya están en el entorno)
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

    filas = _paginas_a_filas(pages)
    print(f"⟳  {len(filas)} jugador(es) procesados.")

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
