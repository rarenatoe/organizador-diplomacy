"""
migrate.py  –  One-time migration from file-based data to SQLite.

Reads existing files in data/ and inserts them into data/diplomacy.db.

What it migrates:
    jugadores_NNNN.csv   → snapshots + snapshot_players  (source='manual')
    reporte_*.txt        → game_events + mesas + mesa_players + waiting_list
                           + output snapshot (source='organizar')
    metadata.json        → sync_events (if present)

Safe to run multiple times: the DB file is deleted and recreated each time,
so there are no duplicate-key issues. Back up diplomacy.db before running
if you have data you want to preserve!

Usage:
    uv run python migrate.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from utils import DIRECTORIO

# ── Import db only for the real run ──────────────────────────────────────────

DATA: Path = DIRECTORIO
SEP: str = "═" * 44


# ── Report parsing (copied from old viewer.py) ────────────────────────────────

def _parse_sections(text: str) -> dict[str, str]:
    parts = re.split(
        r"\n" + re.escape(SEP) + r"\n  (.+?)\n" + re.escape(SEP) + r"\n",
        text,
    )
    sections: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        sections[parts[i].strip()] = parts[i + 1].strip()
    return sections


def _parse_registro(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            k = key.strip()
            if k:
                result[k] = value.strip()
    return result


def _parse_detalle(text: str) -> dict:
    mesas: list[dict] = []
    current_mesa: dict | None = None
    waiting_list: list[dict] = []
    in_waiting = False
    for line in text.splitlines():
        m = re.match(r"^\[ Partida (\d+) \]", line)
        if m:
            in_waiting = False
            gm_match = re.search(r"GM: (.+)$", line)
            current_mesa = {
                "numero": int(m.group(1)),
                "gm": gm_match.group(1).strip() if gm_match else None,
                "jugadores": [],
            }
            mesas.append(current_mesa)
            continue
        if current_mesa is not None:
            p = re.match(r"^\s+\d+\.\s+(.+?)\s+—\s+(.+)$", line)
            if p:
                current_mesa["jugadores"].append({
                    "nombre": p.group(1).strip(),
                    "etiqueta": p.group(2).strip(),
                })
                continue
        if "JUGADORES EN LISTA DE ESPERA" in line:
            in_waiting = True
            continue
        if in_waiting:
            w = re.match(r"^\s+-\s+(.+?)\s+\((.+)\)\s*$", line)
            if w:
                waiting_list.append({
                    "nombre": w.group(1).strip(),
                    "cupos_raw": w.group(2).strip(),
                })
    return {"mesas": mesas, "waiting_list": waiting_list}


def _cupos_int(cupos_raw: str) -> int:
    """Extracts leading integer from '2 cupos sin asignar' → 2."""
    m = re.match(r"(\d+)", cupos_raw)
    return int(m.group(1)) if m else 1


# ── Migration logic ───────────────────────────────────────────────────────────

def migrate(dry_run: bool) -> None:
    import db

    csv_paths = sorted(DATA.glob("jugadores_[0-9][0-9][0-9][0-9].csv"))
    report_paths = sorted(DATA.glob("reporte_*.txt"))
    metadata_path = DATA / "metadata.json"

    if not csv_paths and not report_paths:
        print("⚠️  No hay archivos CSV ni reportes en data/ — nada que migrar.")
        return

    print(f"📂 Encontrados: {len(csv_paths)} CSV(s), {len(report_paths)} reporte(s)")

    if dry_run:
        print("\n── dry-run: mostrando lo que se crearía ──")
        for p in csv_paths:
            rows = list(csv.DictReader(p.open(encoding="utf-8")))
            print(f"  snapshot (manual) ← {p.name} ({len(rows)} jugadores)")
        for p in report_paths:
            text = p.read_text(encoding="utf-8")
            sections = _parse_sections(text)
            reg = _parse_registro(sections.get("REGISTRO", ""))
            print(f"  game_event ← {p.name} (Leído de: {reg.get('Leído de', '?')})")
        print("\n(No se escribió nada)")
        return

    db_path = DATA / "diplomacy.db"
    if db_path.exists():
        print(f"⚠️  Se sobreescribirá {db_path}. Ctrl-C para cancelar.")
        import time
        time.sleep(2)
        db_path.unlink()
        print("   Archivo anterior eliminado.")

    conn = db.get_db(db_path)

    # ── Step 1: CSVs → snapshots ──────────────────────────────────────────────
    csv_to_snap_id: dict[str, int] = {}
    for p in csv_paths:
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        # Use the file mtime as created_at for ordering
        from datetime import datetime
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        snap_id = db.create_snapshot(conn, "manual")
        # Override created_at using direct SQL
        conn.execute("UPDATE snapshots SET created_at = ? WHERE id = ?", (mtime, snap_id))
        for row in rows:
            pid = db.get_or_create_player(conn, row["Nombre"])
            experiencia = row.get("Experiencia", "Antiguo")
            juegos = int(row.get("Juegos_Este_Ano", "0") or "0")
            prioridad_raw = row.get("Prioridad", "False")
            prioridad = 1 if prioridad_raw.strip().lower() in ("true", "1") else 0
            partidas_deseadas = int(row.get("Partidas_Deseadas", "1") or "1")
            partidas_gm = int(row.get("Partidas_GM", "0") or "0")
            db.add_snapshot_player(
                conn, snap_id, pid,
                experiencia, juegos, prioridad, partidas_deseadas, partidas_gm,
            )
        csv_to_snap_id[p.name] = snap_id
        print(f"  ✓ snapshot #{snap_id} ← {p.name} ({len(rows)} jugadores)")

    # ── Step 2: metadata.json → sync_events ──────────────────────────────────
    if metadata_path.exists():
        meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        for record in meta.get("syncs", []):
            leido: str | None = record.get("leido")
            escrito: str | None = record.get("escrito")
            if not escrito:
                continue
            source_snap_id = csv_to_snap_id.get(leido) if leido else None
            output_snap_id = csv_to_snap_id.get(escrito)
            if output_snap_id is None:
                print(f"  ⚠️  sync escrito={escrito} no tiene snapshot — saltando")
                continue
            # Mark the output snapshot's source as notion_sync
            conn.execute(
                "UPDATE snapshots SET source = 'notion_sync' WHERE id = ?",
                (output_snap_id,),
            )
            eid = db.create_sync_event(conn, source_snap_id, output_snap_id)
            print(f"  ✓ sync_event #{eid}: {leido or '(null)'} → {escrito}")

    # ── Step 3: Reports → game_events + mesas ────────────────────────────────
    for p in report_paths:
        text = p.read_text(encoding="utf-8")
        sections = _parse_sections(text)
        reg = _parse_registro(sections.get("REGISTRO", ""))
        detalle = _parse_detalle(sections.get("DETALLE DEL EVENTO", ""))

        leido_csv = reg.get("Leído de", "").strip()
        escrito_csv = reg.get("Escrito en", "").strip()
        generado = reg.get("Generado", "").strip()
        intentos_raw = reg.get("Intentos", "1 de 200").strip()
        intentos = int(intentos_raw.split()[0]) if intentos_raw else 1
        copypaste = sections.get("LISTO PARA COMPARTIR", "")

        input_snap = csv_to_snap_id.get(leido_csv)
        output_snap = csv_to_snap_id.get(escrito_csv)

        if input_snap is None:
            print(f"  ⚠️  {p.name}: Leído de '{leido_csv}' no tiene snapshot — saltando")
            continue
        if output_snap is None:
            print(f"  ⚠️  {p.name}: Escrito en '{escrito_csv}' no tiene snapshot — saltando")
            continue

        # Mark output snapshot source as organizar
        conn.execute(
            "UPDATE snapshots SET source = 'organizar' WHERE id = ?", (output_snap,)
        )
        if generado:
            conn.execute(
                "UPDATE snapshots SET created_at = ? WHERE id = ?", (generado, output_snap)
            )

        ge_id = db.create_game_event(conn, input_snap, output_snap, intentos, copypaste)
        if generado:
            conn.execute("UPDATE game_events SET created_at = ? WHERE id = ?", (generado, ge_id))

        for mesa_data in detalle["mesas"]:
            gm_name: str | None = mesa_data.get("gm")
            gm_pid: int | None = None
            if gm_name:
                gm_pid = db.get_or_create_player(conn, gm_name)
            mesa_id = db.create_mesa(conn, ge_id, mesa_data["numero"], gm_pid)
            for orden, jugador in enumerate(mesa_data["jugadores"], 1):
                pid = db.get_or_create_player(conn, jugador["nombre"])
                db.add_mesa_player(conn, mesa_id, pid, orden)

        for orden, espera in enumerate(detalle["waiting_list"], 1):
            pid = db.get_or_create_player(conn, espera["nombre"])
            cupos = _cupos_int(espera.get("cupos_raw", "1"))
            db.add_waiting_player(conn, ge_id, pid, orden, cupos)

        print(f"  ✓ game_event #{ge_id} ← {p.name} ({len(detalle['mesas'])} mesa(s))")

    conn.commit()
    conn.close()

    # Summary
    snapshots_count = len(csv_paths)
    reports_count = len(report_paths)
    print(f"\n✅ Migración completa: {snapshots_count} snapshot(s), {reports_count} game_event(s)")
    print(f"   Base de datos: {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migra datos existentes de CSV/TXT/metadata.json a SQLite"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué se crearía sin escribir nada",
    )
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
