#!/usr/bin/env python3
"""
viewer.py  –  Visor web local del organizador de Diplomacy.

Uso:
    uv run python -m backend.viewer
    # Abre automáticamente http://127.0.0.1:5001 en el navegador
"""
from __future__ import annotations

import subprocess
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from . import db, db_views

# Configure Flask to find templates and static in frontend/
FRONTEND_PATH = Path(__file__).parent.parent / "frontend"
app = Flask(__name__, template_folder=str(FRONTEND_PATH / "templates"), static_folder=str(FRONTEND_PATH / "static"))


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


@app.route("/api/snapshot/<int:snapshot_id>", methods=["DELETE"])
def api_delete_snapshot(snapshot_id: int):
    conn = db.get_db()
    try:
        if not conn.execute(
            "SELECT 1 FROM snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone():
            return jsonify({"error": "not found"}), 404
        deleted = db.delete_snapshot_cascade(conn, snapshot_id)
        conn.commit()
        return jsonify({"deleted": deleted})
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/api/snapshot/<int:snapshot_id>/edit", methods=["POST"])
def api_edit_snapshot(snapshot_id: int):
    """
    Creates a new 'manual' snapshot branching from snapshot_id.
    Body: {"players": [{"nombre": ..., "prioridad": ...,
                        "partidas_deseadas": ..., "partidas_gm": ...}, ...]}
    Returns: {"snapshot_id": <new_id>}
    """
    conn = db.get_db()
    try:
        if not conn.execute(
            "SELECT 1 FROM snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone():
            return jsonify({"error": "not found"}), 404
        body = request.get_json(silent=True) or {}
        players = body.get("players")
        if not isinstance(players, list):
            return jsonify({"error": "players must be a list"}), 400
        new_id = db.create_manual_snapshot(conn, snapshot_id, players)
        conn.commit()
        return jsonify({"snapshot_id": new_id})
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


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

    cwd = Path(__file__).parent.parent  # project root, so -m backend.X works
    body = request.get_json(silent=True) or {}
    snapshot_id = body.get("snapshot")

    if snapshot_id is not None and not isinstance(snapshot_id, int):
        return jsonify({"error": "snapshot must be an integer"}), 400

    SCRIPT_MODULES = {"organizar": "backend.organizador", "notion_sync": "backend.notion_sync"}
    cmd = ["uv", "run", "python", "-m", SCRIPT_MODULES[script]]
    if snapshot_id is not None:
        cmd += ["--snapshot", str(snapshot_id)]

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

def main() -> None:
    """Start the Flask development server with auto-open browser."""
    threading.Timer(0.8, lambda: webbrowser.open("http://127.0.0.1:5001")).start()
    app.run(debug=False, port=5001)


if __name__ == "__main__":
    main()
