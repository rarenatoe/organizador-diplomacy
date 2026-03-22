"""
notion_sync.py  –  Sincroniza la base de datos de jugadores desde Notion.

Uso:
    uv run python notion_sync.py              # descarga y crea un snapshot en la DB
    uv run python notion_sync.py --dry-run    # muestra lo que se escribiría sin tocar la DB
    uv run python notion_sync.py --force      # fuerza la creación aunque los datos sean idénticos
    uv run python notion_sync.py --detect-only # detecta nombres similares sin crear snapshot
    uv run python notion_sync.py --merges '{"merges": [{"from": "Name1", "to": "Name2"}]}' # aplica fusiones

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
import json
import sys
from datetime import datetime
from difflib import SequenceMatcher

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError
import os

from backend.db import db

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


# ── Name similarity detection ────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, strip, collapse whitespace."""
    return " ".join(name.lower().split())


def _words_match(word_a: str, word_b: str) -> bool:
    """
    Check if two words match, considering abbreviations and prefixes.
    
    Rules:
    - Exact match (case-insensitive)
    - One is a prefix of the other (e.g., "Ren" matches "Renato", "D" matches "Doe")
    - One is abbreviated (ends with ".") and matches the start of the other
      (e.g., "P." matches "Paul", "D." matches "Doe")
    """
    if not word_a or not word_b:
        return False
    
    word_a_lower = word_a.lower().rstrip(".")
    word_b_lower = word_b.lower().rstrip(".")
    
    # Exact match (after removing periods)
    if word_a_lower == word_b_lower:
        return True
    
    # Check if one is a prefix of the other (at least 1 char)
    if len(word_a_lower) >= 1 and len(word_b_lower) >= 1:
        if word_b_lower.startswith(word_a_lower) or word_a_lower.startswith(word_b_lower):
            return True
    
    return False


def _similarity(a: str, b: str) -> float:
    """
    Calculate similarity ratio between two names (0.0 to 1.0).
    
    Uses word-by-word comparison with special handling for abbreviations and prefixes.
    
    The algorithm:
    1. Splits names into words
    2. Compares each word position separately
    3. Returns 1.0 if all words match (considering abbreviations/prefixes)
    4. Returns 0.0 if any word doesn't match
    
    Examples:
    - "Ren Alegre" vs "Renato Alegre" -> 1.0 (first name is prefix, last name exact)
    - "Chachi Faker" vs "Charlie Faker" -> 0.0 (first names don't match)
    - "P. Knight" vs "Paul Knight" -> 1.0 (abbreviated first name matches)
    - "Miguel P." vs "Miguel Paucar" -> 1.0 (abbreviated last name matches)
    - "T. Lopez" vs "Tomas L" -> 1.0 (both abbreviated, both match)
    - "Lori Sanchez" vs "Lori Sal." -> 0.0 (last names don't match)
    - "Gonzalo Ch." vs "Gonzalo L." -> 0.0 (last names don't match)
    """
    norm_a = _normalize_name(a)
    norm_b = _normalize_name(b)
    
    # Handle empty strings
    if not norm_a and not norm_b:
        return 1.0
    if not norm_a or not norm_b:
        return 0.0
    
    words_a = norm_a.split()
    words_b = norm_b.split()
    
    # Must have same number of words
    if len(words_a) != len(words_b):
        return 0.0
    
    # Check each word position
    for word_a, word_b in zip(words_a, words_b):
        if not _words_match(word_a, word_b):
            return 0.0
    
    # All words match
    return 1.0


def _detect_similar_names(
    notion_names: list[str],
    snapshot_names: list[str],
    threshold: float = 0.75,
) -> list[dict]:
    """
    Detect similar names between Notion and snapshot.
    Returns list of potential matches: [{"notion": name1, "snapshot": name2, "similarity": 0.85}]
    Only includes pairs where similarity >= threshold and names are not identical.
    """
    matches: list[dict] = []
    for notion_name in notion_names:
        for snapshot_name in snapshot_names:
            # Skip exact matches
            if _normalize_name(notion_name) == _normalize_name(snapshot_name):
                continue
            sim = _similarity(notion_name, snapshot_name)
            if sim >= threshold:
                matches.append({
                    "notion": notion_name,
                    "snapshot": snapshot_name,
                    "similarity": round(sim, 3),
                })
    # Sort by similarity descending
    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches


# ── Existing player data (from DB) ──────────────────────────────────────

def _leer_snapshot_existente(
    conn: "db.sqlite3.Connection",
    snapshot_id: int | None = None,
) -> dict[str, dict]:
    """Returns nombre → row dict from the given snapshot (or {} if None)."""
    if snapshot_id is None:
        return {}
    return {
        r["nombre"]: r
        for r in db.get_snapshot_players(conn, snapshot_id)
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
    parser.add_argument("--snapshot", type=int, default=None,
                        help="ID del snapshot base (default: último snapshot en la DB)")
    parser.add_argument("--detect-only", action="store_true",
                        help="Detecta nombres similares sin crear snapshot (output JSON)")
    parser.add_argument("--merges", type=str, default=None,
                        help='JSON con fusiones confirmadas: {"merges": [{"from": "Name1", "to": "Name2"}]}')
    args = parser.parse_args()

    load_dotenv()
    token      = os.getenv("NOTION_TOKEN")
    db_id      = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or token.startswith("secret_XXX"):
        print("❌  NOTION_TOKEN no configurado. Copia .env.example → .env y rellénalo.", file=sys.stderr)
        sys.exit(1)
    if not db_id or "XXX" in db_id:
        print("❌  NOTION_DATABASE_ID no configurado. Copia .env.example → .env y rellénalo.", file=sys.stderr)
        sys.exit(1)
    if not part_db_id or "XXX" in part_db_id:
        print("❌  NOTION_PARTICIPACIONES_DB_ID no configurado. Copia .env.example → .env y rellénalo.", file=sys.stderr)
        sys.exit(1)

    año_actual = datetime.now().year
    client = Client(auth=token)

    print("⟳  Conectando a Notion...", end=" ", flush=True)
    try:
        pages = _descargar_todos(client, db_id)
        conteo_por_jugador = _conteo_partidas_este_ano(client, part_db_id, año_actual)
    except APIResponseError as e:
        print(f"\n❌  Error de API Notion: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"{len(pages)} jugador(es), {sum(conteo_por_jugador.values())} partida(s) en {año_actual}.")

    conn = db.get_db()
    source_snapshot_id = (
        args.snapshot if args.snapshot is not None
        else db.get_latest_snapshot_id(conn)
    )
    existentes = _leer_snapshot_existente(conn, source_snapshot_id)

    # ── Parse merges if provided ──────────────────────────────────────────────
    merges: dict[str, str] = {}  # from_name → to_name
    if args.merges:
        try:
            merges_data = json.loads(args.merges)
            for m in merges_data.get("merges", []):
                merges[m["from"]] = m["to"]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌  Error parsing --merges JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # ── Build Notion player lookup (for updating existing players) ──────────
    notion_players: dict[str, dict] = {}
    for page in pages:
        props = page.get("properties", {})
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
        
        notion_players[_normalize_name(nombre)] = {
            "nombre": nombre,
            "experiencia": experiencia,
            "juegos": juegos,
        }
    
    # ── Build new snapshot: start with all existing players, update from Notion ──
    filas: list[dict] = []
    
    if source_snapshot_id is not None:
        # Start with all players from the existing snapshot
        for nombre, existente in existentes.items():
            # Check if this player exists in Notion (exact match)
            normalized_nombre = _normalize_name(nombre)
            if normalized_nombre in notion_players:
                # Update from Notion
                notion_data = notion_players[normalized_nombre]
                filas.append({
                    "Nombre":            nombre,
                    "Experiencia":       notion_data["experiencia"],
                    "Juegos_Este_Ano":   notion_data["juegos"],
                    "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                    "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                    "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                })
            else:
                # Keep existing data (player not in Notion)
                filas.append({
                    "Nombre":            nombre,
                    "Experiencia":       existente.get("experiencia", "Nuevo"),
                    "Juegos_Este_Ano":   int(existente.get("juegos_este_ano", 0)),
                    "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                    "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                    "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                })
    else:
        # No existing snapshot - use all Notion players
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
            
            filas.append({
                "Nombre":            nombre,
                "Experiencia":       experiencia,
                "Juegos_Este_Ano":   juegos,
                "prioridad":         FIELD_DEFAULTS["prioridad"],
                "partidas_deseadas": FIELD_DEFAULTS["partidas_deseadas"],
                "partidas_gm":       FIELD_DEFAULTS["partidas_gm"],
            })

    # ── Detect-only mode: output similar names as JSON ────────────────────────
    if args.detect_only:
        notion_names = [f["Nombre"] for f in filas]
        snapshot_names = list(existentes.keys())
        similar = _detect_similar_names(notion_names, snapshot_names)
        result = {
            "notion_count": len(notion_names),
            "snapshot_count": len(snapshot_names),
            "similar_names": similar,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        conn.close()
        return

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
    if source_snapshot_id is not None and not args.force:
        if db.snapshots_have_same_roster(conn, source_snapshot_id, filas):
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
        db.create_sync_event(conn, source_snapshot_id, snap_id)
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()
    print(f"✓  Snapshot #{snap_id} creado con {len(filas)} jugador(es).")
    if source_snapshot_id is not None:
        print(f"   sync_event: snapshot #{source_snapshot_id} → #{snap_id}")
    else:
        print("   (primer sync — sin snapshot anterior)")


if __name__ == "__main__":
    main()
