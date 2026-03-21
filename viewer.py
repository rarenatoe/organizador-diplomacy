#!/usr/bin/env python3
"""
viewer.py  –  Visor web local del organizador de Diplomacy.

Uso:
    uv run python viewer.py
    # Abre automáticamente http://127.0.0.1:5000 en el navegador
"""
from __future__ import annotations

import csv
import re
import subprocess
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from utils import DIRECTORIO

app = Flask(__name__)
DATA: Path = DIRECTORIO
SEP_SECTION: str = "═" * 44


# ── Report parsing ─────────────────────────────────────────────────────────────

def _parse_report_sections(text: str) -> dict[str, str]:
    """Splits a report file into its 4 named sections."""
    parts = re.split(
        r"\n" + re.escape(SEP_SECTION) + r"\n  (.+?)\n" + re.escape(SEP_SECTION) + r"\n",
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
    """Parses DETALLE DEL EVENTO section into structured mesas + waiting_list."""
    mesas: list[dict] = []
    current_mesa: dict | None = None
    waiting_list: list[dict] = []
    in_waiting = False

    for line in text.splitlines():
        # Mesa header: [ Partida N ]  Nuevos: X  Antiguos: Y  GM: nombre
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

        # Player line: "  1. Nombre  —  Etiqueta"
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
                    "cupos": w.group(2).strip(),
                })

    return {"mesas": mesas, "waiting_list": waiting_list}


def _parse_proyeccion(text: str) -> list[dict]:
    """Parses PROYECCIÓN section into table rows (skip 2-line header)."""
    rows: list[dict] = []
    for line in text.splitlines()[2:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 5:
            rows.append({
                "nombre":     " ".join(parts[:-4]),
                "actual":     parts[-4],
                "jugadas":    parts[-3],
                "gm":         parts[-2],
                "proyectado": parts[-1],
            })
    return rows


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Chain builder ──────────────────────────────────────────────────────────────

def _build_chain() -> dict:
    """
    Builds the node list by following actual data lineage (Leído de / Escrito en)
    instead of relying on CSV filename order alone.

    Algorithm:
      1. Parse every report's REGISTRO to extract (leido, escrito) edges.
      2. Root CSVs = CSVs with no parent report (notion_sync output or initial).
      3. DFS from each root: CSV → its reports (sorted by name/time) → each
         output CSV → …
      4. Any CSVs unreachable from roots (shouldn't happen) appended at the end.
    """
    csvs: dict[str, Path] = {p.name: p for p in sorted(DATA.glob("jugadores_*.csv"))}
    report_paths: list[Path] = sorted(DATA.glob("reporte_*.txt"))

    # Parse every report once
    report_meta: dict[str, dict] = {}  # report_name → {registro, leido, escrito}
    for rpt in report_paths:
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        registro = _parse_registro(sections.get("REGISTRO", ""))
        leido   = registro.get("Leído de",  "").strip()
        escrito = registro.get("Escrito en", "").strip()
        if leido:
            report_meta[rpt.name] = {
                "registro": registro,
                "leido":    leido,
                "escrito":  escrito,
            }

    # csv_name → [sorted report names that read from this CSV]
    csv_to_reports: dict[str, list[str]] = {}
    for rname, meta in report_meta.items():
        csv_to_reports.setdefault(meta["leido"], []).append(rname)
    for lst in csv_to_reports.values():
        lst.sort()  # report filenames are timestamp-based → chronological order

    # output_csv → report that produced it
    produced_by: dict[str, str] = {
        meta["escrito"]: rname
        for rname, meta in report_meta.items()
        if meta["escrito"]
    }

    pending  = (DATA / ".pending").exists()
    all_csvs = sorted(csvs)
    latest   = all_csvs[-1] if all_csvs else None

    if not csvs:
        return {"nodes": [], "pending": pending}

    # Root CSVs: not produced by any report (notion_sync output or initial import)
    root_csvs = [c for c in all_csvs if c not in produced_by]

    nodes:   list[dict] = []
    visited: set[str]   = set()

    def _csv_node(name: str) -> dict:
        players = _read_csv(csvs[name])
        return {
            "type":         "csv",
            "filename":     name,
            "player_count": len(players),
            "is_latest":    name == latest,
            "pending":      name == latest and pending,
        }

    def _walk(csv_name: str) -> None:
        if csv_name in visited or csv_name not in csvs:
            return
        visited.add(csv_name)
        nodes.append(_csv_node(csv_name))
        for rname in csv_to_reports.get(csv_name, []):
            meta = report_meta[rname]
            reg  = meta["registro"]
            nodes.append({
                "type":      "report",
                "filename":  rname,
                "generated": reg.get("Generado", ""),
                "partidas":  reg.get("Partidas",  ""),
                "en_espera": reg.get("En espera", ""),
                "intentos":  reg.get("Intentos",  ""),
                "leido":     meta["leido"],
                "escrito":   meta["escrito"],
            })
            _walk(meta["escrito"])

    for root in root_csvs:
        _walk(root)

    # Safety net: append any CSVs not reached by the DFS
    for name in all_csvs:
        if name not in visited:
            nodes.append(_csv_node(name))

    return {"nodes": nodes, "pending": pending}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chain")
def api_chain():
    return jsonify(_build_chain())


@app.route("/api/csv/<filename>")
def api_csv(filename: str):
    if not re.match(r"^jugadores_\d{4}\.csv$", filename):
        return jsonify({"error": "invalid filename"}), 400
    path = DATA / filename
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    return jsonify({"filename": filename, "rows": _read_csv(path)})


@app.route("/api/report/<filename>")
def api_report(filename: str):
    if not re.match(r"^reporte_.+\.txt$", filename):
        return jsonify({"error": "invalid filename"}), 400
    path = DATA / filename
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    text = path.read_text(encoding="utf-8")
    sections = _parse_report_sections(text)
    return jsonify({
        "filename":   filename,
        "copypaste":  sections.get("LISTO PARA COMPARTIR", ""),
        "detalle":    _parse_detalle(sections.get("DETALLE DEL EVENTO", "")),
        "proyeccion": _parse_proyeccion(sections.get("PROYECCIÓN JUEGOS_ESTE_AÑO", "")),
        "registro":   _parse_registro(sections.get("REGISTRO", "")),
    })


@app.route("/api/csvs")
def api_csvs():
    """Lists all jugadores_NNNN.csv files available as organizar sources."""
    files = sorted(p.name for p in DATA.glob("jugadores_*.csv"))
    return jsonify({"csvs": files})


@app.route("/api/run/<script>", methods=["POST"])
def api_run(script: str):
    if script not in ("notion_sync", "organizar"):
        return jsonify({"error": "unknown script"}), 400

    cwd = Path(__file__).parent

    if script == "organizar":
        body = request.get_json(silent=True) or {}
        csv_name: str | None = body.get("csv")
        cmd = ["uv", "run", "python", "organizador.py"]
        if csv_name:
            if not re.match(r"^jugadores_\d{4}\.csv$", csv_name):
                return jsonify({"error": "invalid csv name"}), 400
            csv_full = str(DATA / csv_name)
            cmd += ["--csv", csv_full]
    else:
        cmd = ["uv", "run", "python", "notion_sync.py"]

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return jsonify({
        "returncode": result.returncode,
        "stdout":     result.stdout,
        "stderr":     result.stderr,
    })


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    threading.Timer(0.8, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=False, port=5000)
