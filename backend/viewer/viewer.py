#!/usr/bin/env python3
"""
viewer.py  –  Visor web local del organizador de Diplomacy.

Uso:
    uv run python -m backend.viewer
    # Abre automáticamente http://127.0.0.1:5001 en el navegador
"""
from __future__ import annotations

import json
import subprocess
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

from backend.config import FLASK_TEMPLATE_DIR, FLASK_STATIC_DIR, PROJECT_ROOT
from backend.db import db, db_views

# Configure Flask to find templates and static in frontend/
app = Flask(__name__, template_folder=str(FLASK_TEMPLATE_DIR), static_folder=str(FLASK_STATIC_DIR))


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


@app.route("/api/snapshot/new", methods=["POST"])
def api_create_snapshot():
    """
    Creates a new root 'manual' snapshot (no source snapshot).
    Body: {"players": [{"nombre": ..., "experiencia": ..., "juegos_este_ano": ...,
                        "prioridad": ..., "partidas_deseadas": ..., "partidas_gm": ...}, ...]}
    Returns: {"snapshot_id": <new_id>}
    """
    conn = db.get_db()
    try:
        body = request.get_json(silent=True) or {}
        players = body.get("players")
        if not isinstance(players, list):
            return jsonify({"error": "players must be a list"}), 400
        new_id = db.create_root_manual_snapshot(conn, players)
        conn.commit()
        return jsonify({"snapshot_id": new_id})
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

    cwd = PROJECT_ROOT  # project root, so -m backend.X works
    body = request.get_json(silent=True) or {}
    snapshot_id = body.get("snapshot")

    # organizar always requires snapshot_id
    # notion_sync allows empty snapshot_id (first-time sync exception handled in notion_sync.py)
    if script == "organizar" and snapshot_id is None:
        return jsonify({"error": "Snapshot selection required. Please click a snapshot node in the chain before syncing or organizing."}), 400

    if snapshot_id is not None and not isinstance(snapshot_id, int):
        return jsonify({"error": "snapshot must be an integer"}), 400

    SCRIPT_MODULES = {"organizar": "backend.organizador.organizador", "notion_sync": "backend.sync.notion_sync"}
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


@app.route("/api/sync/detect", methods=["POST"])
def api_sync_detect():
    """
    Detect similar names between Notion and snapshot.
    Body: {"snapshot": <int_id>}
    Returns: {"notion_count", "snapshot_count", "similar_names": [...]}
    """
    cwd = PROJECT_ROOT
    body = request.get_json(silent=True) or {}
    snapshot_id = body.get("snapshot")

    if snapshot_id is None:
        return jsonify({"error": "Snapshot selection required. Please click a snapshot node in the chain before syncing or organizing."}), 400

    if not isinstance(snapshot_id, int):
        return jsonify({"error": "snapshot must be an integer"}), 400

    cmd = ["uv", "run", "python", "-m", "backend.sync.notion_sync", "--detect-only", "--snapshot", str(snapshot_id)]

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=90,
    )

    if result.returncode != 0:
        return jsonify({
            "error": "Detection failed",
            "stderr": result.stderr,
        }), 500

    try:
        # Parse JSON from stdout (skip any non-JSON lines)
        stdout = result.stdout
        # Find the JSON output (starts with '{')
        json_start = stdout.find("{")
        if json_start == -1:
            return jsonify({"error": "No JSON output from detection"}), 500
        data = json.loads(stdout[json_start:])
        return jsonify(data)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse detection output: {e}"}), 500


@app.route("/api/sync/confirm", methods=["POST"])
def api_sync_confirm():
    """
    Confirm sync with optional merges.
    Body: {"snapshot": <int_id>, "merges": [{"from": "Name1", "to": "Name2"}, ...]}
    Returns: {"returncode", "stdout", "stderr"}
    """
    cwd = PROJECT_ROOT
    body = request.get_json(silent=True) or {}
    snapshot_id = body.get("snapshot")
    merges = body.get("merges", [])

    if snapshot_id is None:
        return jsonify({"error": "Snapshot selection required. Please click a snapshot node in the chain before syncing or organizing."}), 400

    if not isinstance(snapshot_id, int):
        return jsonify({"error": "snapshot must be an integer"}), 400

    cmd = ["uv", "run", "python", "-m", "backend.sync.notion_sync", "--snapshot", str(snapshot_id)]

    if merges:
        merges_json = json.dumps({"merges": merges}, ensure_ascii=False)
        cmd += ["--merges", merges_json]

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


@app.route("/api/player/rename", methods=["POST"])
def api_player_rename():
    """
    Rename a player in the players table.
    Body: {"old_name": "Turk", "new_name": "Kurt"}
    Returns: {"success": true} or {"error": "..."}
    """
    conn = db.get_db()
    try:
        body = request.get_json(silent=True) or {}
        old_name = body.get("old_name")
        new_name = body.get("new_name")
        
        if not old_name or not new_name:
            return jsonify({"error": "old_name and new_name are required"}), 400
        
        if old_name == new_name:
            return jsonify({"error": "old_name and new_name are the same"}), 400
        
        success = db.rename_player(conn, old_name, new_name)
        if not success:
            return jsonify({"error": "Jugador no encontrado o el nuevo nombre ya existe"}), 404
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/api/snapshot/<int:snapshot_id>/add-player", methods=["POST"])
def api_add_player(snapshot_id: int):
    """
    Add a player to a snapshot.
    Body: {"nombre": "Player Name", "experiencia": "Nuevo", "juegos_este_ano": 0,
           "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0}
    Returns: {"player_id": <int>} or {"error": "..."}
    """
    conn = db.get_db()
    try:
        if not conn.execute(
            "SELECT 1 FROM snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone():
            return jsonify({"error": "snapshot not found"}), 404
        
        body = request.get_json(silent=True) or {}
        nombre = body.get("nombre")
        if not nombre:
            return jsonify({"error": "nombre is required"}), 400
        
        experiencia = body.get("experiencia", "Nuevo")
        juegos_este_ano = int(body.get("juegos_este_ano", 0))
        prioridad = int(body.get("prioridad", 0))
        partidas_deseadas = int(body.get("partidas_deseadas", 1))
        partidas_gm = int(body.get("partidas_gm", 0))
        
        player_id = db.add_player_to_snapshot(
            conn, snapshot_id, nombre,
            experiencia, juegos_este_ano,
            prioridad, partidas_deseadas, partidas_gm
        )
        conn.commit()
        return jsonify({"player_id": player_id})
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Start the Flask development server with auto-open browser."""
    threading.Timer(0.8, lambda: webbrowser.open("http://127.0.0.1:5001")).start()
    app.run(debug=False, port=5001)


if __name__ == "__main__":
    main()
