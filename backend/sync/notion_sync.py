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
import concurrent.futures
import difflib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

from backend.db import db

# ── Player field defaults for first-time Notion players ──────────────────────

FIELD_DEFAULTS: dict[str, int] = {
    "prioridad":         0,
    "partidas_deseadas": 1,
    "partidas_gm":       0,
}

# ── Country property mapping ──────────────────────────────────────────────────

COUNTRY_PROPS: dict[str, str] = {
    "c_england": "∀ 🇬🇧",
    "c_france":  "∀ 🇫🇷",
    "c_germany": "∀ 🇩🇪",
    "c_italy":   "∀ 🇮🇹",
    "c_austria": "∀ 🇦🇹",
    "c_russia":  "∀ 🇷🇺",
    "c_turkey":  "∀ 🇹🇷",
}

# ── Helpers de extracción ─────────────────────────────────────────────────────

def _extraer_numero(prop: dict) -> int:
    """Extrae un número de una propiedad number o formula."""
    if not prop:
        return 0
    if prop.get("type") == "number":
        return int(prop.get("number") or 0)
    if prop.get("type") == "formula":
        return int(prop.get("formula", {}).get("number") or 0)
    return 0


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


def _words_match(word_a: str, word_b: str) -> float:
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
    if (len(wa) >= 1 and len(wb) >= 1 and 
        (wb.startswith(wa) or wa.startswith(wb))):
        return 0.8 # Prefix match is good but not perfect
        
    # Probabilistic match for typos
    return difflib.SequenceMatcher(None, wa, wb).ratio()


def _similarity(a: str, b: str) -> float:
    """
    Calculate similarity ratio between two names (0.0 to 1.0).
    Uses Token-Set + Probabilistic matching.
    """
    norm_a = _normalize_name(a)
    norm_b = _normalize_name(b)
    
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
    used_long_indices = set()
    
    for sw in short_words:
        best_word_sim = 0.0
        best_idx = -1
        
        for i, lw in enumerate(long_words):
            if i in used_long_indices:
                continue
            sim = _words_match(sw, lw)
            if sim > best_word_sim:
                best_word_sim = sim
                best_idx = i
        
        if best_word_sim >= 0.85: # High confidence word match
            matched_count += 1.0
            used_long_indices.add(best_idx)
        elif best_word_sim >= 0.5: # Partial word match
            matched_count += best_word_sim
            used_long_indices.add(best_idx)
            
    # Score is matched words over total words in the longer name
    score = matched_count / len(long_words)
    
    # BONUS: If it's a perfect prefix match (all words of shorter name match)
    # and the difference is only 1 word, we boost the similarity to 0.8
    if matched_count == len(short_words) and len(long_words) - len(short_words) == 1:
        return max(0.8, score)
        
    return score


def _detect_similar_names(
    notion_players: dict[str, dict] | list[dict],
    snapshot_names: list[str],
    threshold: float = 0.75,
) -> list[dict]:
    """
    Detect similar names between Notion (including aliases) and snapshot
    using a 4-step waterfall algorithm.
    """
    # Normalize notion_players input to list of dicts if it's a map
    players_list = (
        list(notion_players.values()) if isinstance(notion_players, dict) 
        else notion_players
    )
    
    # Pre-normalize all snapshot names for Step 1 & 2
    norm_snapshots = {name: _normalize_name(name) for name in snapshot_names}
    
    potential_matches = []
    
    # Step 1 & 2: Exact & Alias Matches (Filter them out)
    # We want to find names that DON'T match exactly but are similar
    remaining_snapshots = list(snapshot_names)
    
    # Track exact matches to avoid comparing them for similarity
    exact_matches_snapshot = set()
    
    for player_data in players_list:
        notion_main_name = player_data["nombre"]
        norm_notion_main = _normalize_name(notion_main_name)
        notion_aliases = [_normalize_name(a) for a in player_data.get("alias", [])]
        
        for snap_name in snapshot_names:
            norm_snap = norm_snapshots[snap_name]
            
            # Step 1: Exact Match
            if norm_notion_main == norm_snap:
                exact_matches_snapshot.add(snap_name)
                continue
                
            # Step 2: Explicit Alias Match
            if norm_snap in notion_aliases:
                exact_matches_snapshot.add(snap_name)
                continue

    # Step 3: Hybrid Fuzzy Matching
    # Only compare snapshots that didn't have an exact match with ANY notion player
    # and notion players that didn't have an exact match with THIS snapshot
    for player_data in players_list:
        notion_main_name = player_data["nombre"]
        notion_variations = [notion_main_name] + player_data.get("alias", [])
        
        for snap_name in snapshot_names:
            if snap_name in exact_matches_snapshot:
                continue
                
            # Check similarity against all variations, keep best
            best_sim = 0.0
            for var in notion_variations:
                sim = _similarity(var, snap_name)
                if sim > best_sim:
                    best_sim = sim
            
            if best_sim >= threshold:
                potential_matches.append({
                    "notion": notion_main_name,
                    "snapshot": snap_name,
                    "similarity": round(best_sim, 3)
                })

    # Step 4: Bi-Directional Ambiguity Detection (1-to-Many)
    # If a name maps to multiple candidates, they are all conflicts.
    # Group by notion and by snapshot to detect 1-to-Many in both directions.
    notion_to_snaps = defaultdict(set)
    snap_to_notions = defaultdict(set)
    
    for m in potential_matches:
        notion_to_snaps[m["notion"]].add(m["snapshot"])
        snap_to_notions[m["snapshot"]].add(m["notion"])
        
    # All potential matches found in Step 3 are technically conflicts 
    # since they are not exact matches but are above threshold.
    # The ambiguity detection is already implicit if we return all matches.
    # We just need to make sure they are unique and sorted.
    
    unique_matches = []
    seen = set()
    for m in potential_matches:
        key = (m["notion"], m["snapshot"])
        if key not in seen:
            unique_matches.append(m)
            seen.add(key)
            
    unique_matches.sort(key=lambda x: x["similarity"], reverse=True)
    return unique_matches


# ── Existing player data (from DB) ──────────────────────────────────────

def _leer_snapshot_existente(
    conn: db.sqlite3.Connection,
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

def conteo_partidas_este_ano(
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
        kwargs: dict = {
            "data_source_id": ds_id,
            "result_type": "page",
            "filter": {
                "property": "Temporada",
                "rollup": {
                    "number": {
                        "equals": año
                    }
                }
            }
        }
        if prop_ids:
            kwargs["filter_properties"] = prop_ids
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


# ── Descarga desde Notion ─────────────────────────────────────────────────────

def descargar_todos(
    client: Client,
    database_id: str,
) -> list[dict]:
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

    # Payload reduction: get property IDs for required fields
    prop_ids: list[str] = []
    props = db_info.get("properties", {})
    required_names = ["Nombre", "Participaciones", "Alias"] + list(COUNTRY_PROPS.values())
    for name in required_names:
        if name in props:
            prop_ids.append(props[name]["id"])

    pages: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs: dict = {
            "data_source_id": data_source_id,
            "result_type": "page",
        }
        if prop_ids:
            kwargs["filter_properties"] = prop_ids
        if cursor:
            kwargs["start_cursor"] = cursor
        response = client.data_sources.query(**kwargs)
        pages.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return pages


def _find_notion_player(name: str, notion_players: dict[str, dict]) -> dict | None:
    """Finds a Notion player by name or alias."""
    norm_name = _normalize_name(name)
    # Exact name match
    if norm_name in notion_players:
        return notion_players[norm_name]
    # Alias match
    for p in notion_players.values():
        if norm_name in p.get("alias", []):
            return p
    return None


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
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_pages = executor.submit(descargar_todos, client, db_id)
            future_conteo = executor.submit(conteo_partidas_este_ano, client, part_db_id, año_actual)
            
            pages = future_pages.result()
            conteo_por_jugador = future_conteo.result()
    except APIResponseError as e:
        print(f"\n❌  Error de API Notion: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"{len(pages)} jugador(es), {sum(conteo_por_jugador.values())} partida(s) en {año_actual}.")

    conn = db.get_db()
    source_snapshot_id = args.snapshot

    # ── Require snapshot if database has existing data ────────────────────────
    has_snapshots = conn.execute("SELECT 1 FROM snapshots LIMIT 1").fetchone() is not None
    if source_snapshot_id is None and has_snapshots:
        print("❌  Error: Snapshot ID is required because the database is not empty.", file=sys.stderr)
        print("   You must specify which snapshot to branch from.", file=sys.stderr)
        print("   Usa --snapshot <ID> para especificar el snapshot base.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    existentes = _leer_snapshot_existente(conn, source_snapshot_id)

    # ── Parse merges if provided ──────────────────────────────────────────────
    merges: dict[str, dict] = {}  # from_name → {"to": notion_name, "action": action}
    if args.merges:
        try:
            merges_data = json.loads(args.merges)
            for m in merges_data.get("merges", []):
                merges[m["from"]] = {"to": m["to"], "action": m.get("action", "merge_local")}
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
        
        # Alias extraction
        alias_prop = props.get("Alias")
        alias_text = "".join(p.get("plain_text", "") for p in alias_prop.get("rich_text", [])) if alias_prop else ""
        alias_list = [a.strip().lower() for a in alias_text.split(",") if a.strip()]
        
        # Country history extraction
        countries_data = {
            key: _extraer_numero(props.get(notion_name, {}))
            for key, notion_name in COUNTRY_PROPS.items()
        }
        
        notion_players[_normalize_name(nombre)] = {
            "notion_id": page["id"],
            "nombre": nombre,
            "experiencia": experiencia,
            "juegos": juegos,
            "alias": alias_list,
            **countries_data,
        }
    
    # ── Detect-only mode: output similar names as JSON ────────────────────────
    # We must do this BEFORE building `filas` so we use the raw incoming Notion names
    if args.detect_only:
        snapshot_names = list(existentes.keys())
        similar = _detect_similar_names(notion_players, snapshot_names)
        result = {
            "notion_count": len(notion_players),
            "snapshot_count": len(snapshot_names),
            "similar_names": similar,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        conn.close()
        return

    # ── Build new snapshot: start with all existing players, update from Notion ──
    filas: list[dict] = []
    
    if source_snapshot_id is not None:
        merged_notion_normalized = {_normalize_name(v["to"]) for v in merges.values()}
        
        # Start with all players from the existing snapshot
        for nombre, existente in existentes.items():
            # 1. Check if this player was explicitly merged via the UI dialog
            if nombre in merges:
                merge_info = merges[nombre]
                notion_name = merge_info["to"]
                action = merge_info["action"]
                notion_norm = _normalize_name(notion_name)
                
                if notion_norm in notion_players:
                    notion_data = notion_players[notion_norm]
                    filas.append({
                        "Nombre":            notion_data["nombre"] if action == "merge_notion" else nombre,
                        "Experiencia":       notion_data["experiencia"],
                        "Juegos_Este_Ano":   notion_data["juegos"],
                        "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                        "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                        "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                        **{c: notion_data[c] for c in COUNTRY_PROPS},
                    })
                    continue
            
            # 2. Check if this player exists in Notion (exact match or alias match)
            notion_data = _find_notion_player(nombre, notion_players)
            if notion_data and _normalize_name(notion_data["nombre"]) not in merged_notion_normalized:
                filas.append({
                    "Nombre":            nombre, # Keep local name
                    "Experiencia":       notion_data["experiencia"],
                    "Juegos_Este_Ano":   notion_data["juegos"],
                    "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                    "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                    "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                    **{c: notion_data[c] for c in COUNTRY_PROPS},
                })
            elif nombre not in merges:
                # 3. Keep existing data (player not in Notion and not merged)
                filas.append({
                    "Nombre":            nombre,
                    "Experiencia":       existente.get("experiencia", "Nuevo"),
                    "Juegos_Este_Ano":   int(existente.get("juegos_este_ano", 0)),
                    "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                    "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                    "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                    **{c: existente.get(c, 0) for c in COUNTRY_PROPS},
                })

    else:
        # No existing snapshot - use all Notion players directly from our lookup
        for _, notion_data in notion_players.items():
            filas.append({
                "Nombre":            notion_data["nombre"],
                "Experiencia":       notion_data["experiencia"],
                "Juegos_Este_Ano":   notion_data["juegos"],
                "prioridad":         FIELD_DEFAULTS["prioridad"],
                "partidas_deseadas": FIELD_DEFAULTS["partidas_deseadas"],
                "partidas_gm":       FIELD_DEFAULTS["partidas_gm"],
                **{c: notion_data[c] for c in COUNTRY_PROPS},
            })

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
    if source_snapshot_id is not None and not args.force and db.snapshots_have_same_roster(conn, source_snapshot_id, filas):
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
                fila["c_england"],
                fila["c_france"],
                fila["c_germany"],
                fila["c_italy"],
                fila["c_austria"],
                fila["c_russia"],
                fila["c_turkey"],
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
