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
from backend.sync.notion_sync import _descargar_todos, _conteo_partidas_este_ano
from dotenv import load_dotenv
from notion_client import Client
import os

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


@app.route("/api/notion/fetch", methods=["GET"])
def api_notion_fetch():
    """
    Fetches raw player data from Notion without writing to the database.
    Returns: {"players": [{"nombre": "...", "experiencia": "Nuevo", "juegos_este_ano": 0}, ...]}
    """
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or token.startswith("secret_XXX"):
        return jsonify({"error": "NOTION_TOKEN not configured"}), 500
    if not db_id or "XXX" in db_id:
        return jsonify({"error": "NOTION_DATABASE_ID not configured"}), 500
    if not part_db_id or "XXX" in part_db_id:
        return jsonify({"error": "NOTION_PARTICIPACIONES_DB_ID not configured"}), 500

    try:
        from datetime import datetime
        client = Client(auth=token)
        año_actual = datetime.now().year

        pages = _descargar_todos(client, db_id)
        conteo_por_jugador = _conteo_partidas_este_ano(client, part_db_id, año_actual)

        players: list[dict] = []
        for page in pages:
            props = page.get("properties", {})

            # Nombre
            nombre_prop = props.get("Nombre")
            if not nombre_prop:
                continue
            nombre = "".join(p.get("plain_text", "") for p in nombre_prop.get("title", [])).strip()
            if not nombre:
                continue

            # Experiencia
            part_prop = props.get("Participaciones")
            experiencia = "Antiguo" if part_prop and part_prop.get("relation") else "Nuevo"

            # Juegos_Este_Ano
            player_id = page["id"].replace("-", "")
            juegos = conteo_por_jugador.get(player_id, 0)

            players.append({
                "nombre": nombre,
                "experiencia": experiencia,
                "juegos_este_ano": juegos,
            })

        return jsonify({"players": players})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/snapshot/save", methods=["POST"])
def api_snapshot_save():
    """
    Unified endpoint to save a new snapshot from a player list.
    Body: {"parent_id": int | null, "event_type": "manual" | "sync", "players": [...]}
    Returns: {"snapshot_id": <new_id>}
    """
    conn = db.get_db()
    try:
        body = request.get_json(silent=True) or {}
        parent_id = body.get("parent_id")
        event_type = body.get("event_type", "manual")
        players = body.get("players")

        if not isinstance(players, list):
            return jsonify({"error": "players must be a list"}), 400

        if event_type not in ("manual", "sync"):
            return jsonify({"error": "event_type must be 'manual' or 'sync'"}), 400

        if parent_id is not None and not isinstance(parent_id, int):
            return jsonify({"error": "parent_id must be an integer or null"}), 400

        # Validate parent exists if provided
        if parent_id is not None:
            parent_row = conn.execute(
                "SELECT source FROM snapshots WHERE id = ?", (parent_id,)
            ).fetchone()
            if not parent_row:
                return jsonify({"error": "parent snapshot not found"}), 404

            # STRICT GUARD: Prevent consecutive syncs
            if event_type == "sync" and parent_row["source"] == "notion_sync":
                return jsonify({"error": "El snapshot base ya fue generado por notion_sync y aún no se ha jugado una partida."}), 400

        # Create snapshot with appropriate source
        source = "notion_sync" if event_type == "sync" else "manual"
        snap_id = db.create_snapshot(conn, source)

        # Add players with defaults for missing fields
        for player in players:
            nombre = player.get("nombre", "")
            if not nombre:
                continue
            player_id = db.get_or_create_player(conn, nombre)
            db.add_snapshot_player(
                conn, snap_id, player_id,
                player.get("experiencia", "Nuevo"),
                int(player.get("juegos_este_ano", 0)),
                int(player.get("prioridad", 0)),
                int(player.get("partidas_deseadas", 1)),
                int(player.get("partidas_gm", 0)),
            )

        # Create event linking parent to new snapshot if parent provided
        # Map event_type to valid event types: 'sync' -> 'sync', 'manual' -> 'edit'
        if parent_id is not None:
            db_event_type = "sync" if event_type == "sync" else "edit"
            db.create_event(conn, db_event_type, parent_id, snap_id)

        conn.commit()
        return jsonify({"snapshot_id": snap_id})
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
