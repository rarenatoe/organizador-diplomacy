#!/usr/bin/env python3
"""
viewer.py  –  Visor web local del organizador de Diplomacy.

Uso:
    uv run python viewer.py
    # Abre automáticamente http://127.0.0.1:5000 en el navegador
"""
from __future__ import annotations

import subprocess
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import db
import db_views

app = Flask(__name__)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chain")
def api_chain():
    conn = db.get_db()
    try:
        data = db_views.build_chain_data(conn)
    finally:
        conn.close()
    return jsonify(data)


@app.route("/api/snapshot/<int:snapshot_id>")
def api_snapshot(snapshot_id: int):
    conn = db.get_db()
    try:
        detail = db_views.get_snapshot_detail(conn, snapshot_id)
    finally:
        conn.close()
    if detail is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(detail)


@app.route("/api/game/<int:game_event_id>")
def api_game(game_event_id: int):
    conn = db.get_db()
    try:
        detail = db_views.get_game_event_detail(conn, game_event_id)
    finally:
        conn.close()
    if detail is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(detail)


@app.route("/api/snapshots")
def api_snapshots():
    """Lists all snapshots available as organizar sources."""
    conn = db.get_db()
    try:
        rows = conn.execute(
            "SELECT id, created_at, source FROM snapshots ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return jsonify({"snapshots": [dict(r) for r in rows]})


@app.route("/api/run/<script>", methods=["POST"])
def api_run(script: str):
    if script not in ("notion_sync", "organizar"):
        return jsonify({"error": "unknown script"}), 400

    cwd = Path(__file__).parent

    if script == "organizar":
        body = request.get_json(silent=True) or {}
        snapshot_id = body.get("snapshot")
        cmd = ["uv", "run", "python", "organizador.py"]
        if snapshot_id is not None:
            if not isinstance(snapshot_id, int):
                return jsonify({"error": "snapshot must be an integer"}), 400
            cmd += ["--snapshot", str(snapshot_id)]
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
