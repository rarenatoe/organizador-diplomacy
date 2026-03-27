#!/usr/bin/env python3
"""
viewer.py  –  Visor web local del organizador de Diplomacy.

Uso:
    uv run python -m backend.viewer
    # Abre automáticamente http://127.0.0.1:5001 en el navegador
"""
from __future__ import annotations

import os
import subprocess
import threading
import webbrowser
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from notion_client import Client

from backend.config import FLASK_STATIC_DIR, FLASK_TEMPLATE_DIR, PROJECT_ROOT
from backend.db import db, db_views
from backend.organizador.core import calcular_partidas
from backend.organizador.models import Jugador
from backend.organizador.persistence import save_game_draft
from backend.sync.cache_daemon import start_background_sync, update_notion_cache
from backend.sync.notion_sync import (
    _detect_similar_names,  # pyright: ignore[reportPrivateUsage]
)

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
        body: dict[str, Any] = request.get_json(silent=True) or {}
        players: list[dict[str, Any]] | None = body.get("players")
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


@app.route("/api/notion/fetch", methods=["POST"])
def api_notion_fetch():
    """
    Fetches raw player data from the local notion_cache table.
    Optionally detects similar names if snapshot_names is provided in body.
    Body: {"snapshot_names": ["Name1", "Name2", ...]}
    Returns: {"players": [...], "similar_names": [...], "last_updated": "..."}
    """
    conn = db.get_db()
    try:
        body: dict[str, Any] = request.get_json(silent=True) or {}
        snapshot_names = body.get("snapshot_names", [])

        rows = conn.execute("SELECT * FROM notion_cache ORDER BY nombre").fetchall()
        if not rows:
            return jsonify({"players": [], "similar_names": [], "last_updated": None})

        players: list[dict[str, Any]] = []
        last_updated = rows[0]["last_updated"] if rows else None
        
        for r in rows:
            players.append({
                "nombre":          r["nombre"],
                "experiencia":     r["experiencia"],
                "juegos_este_ano": r["juegos_este_ano"],
                "c_england":       r["c_england"],
                "c_france":        r["c_france"],
                "c_germany":       r["c_germany"],
                "c_italy":         r["c_italy"],
                "c_austria":       r["c_austria"],
                "c_russia":        r["c_russia"],
                "c_turkey":        r["c_turkey"],
            })

        similar_names = []
        if snapshot_names:
            similar_names = _detect_similar_names(players, snapshot_names)

        return jsonify({
            "players": players,
            "similar_names": similar_names,
            "last_updated": last_updated
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/api/notion/force_refresh", methods=["POST"])
def api_notion_force_refresh():
    """
    Manually triggers a Notion cache update synchronously.
    Returns: {"success": true, "message": "..."}
    """
    load_dotenv()
    token      = os.getenv("NOTION_TOKEN")
    db_id      = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or not db_id or not part_db_id or token.startswith("secret_XXX"):
        return jsonify({"error": "Notion credentials not configured"}), 500

    client = Client(auth=token)
    conn = db.get_db()
    try:
        update_notion_cache(conn, client, db_id, part_db_id)
        return jsonify({"success": True, "message": "Cache updated successfully"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/api/snapshot/save", methods=["POST"])
def api_snapshot_save():
    """
    Unified endpoint to save a new snapshot from a player list.
    Body: {"parent_id": int | null, "event_type": "manual" | "sync", "players": [...]}
    Returns: {"snapshot_id": <new_id>}
    """
    conn = db.get_db()
    try:
        body: dict[str, Any] = request.get_json(silent=True) or {}
        parent_id: int | None = body.get("parent_id")
        event_type: str = body.get("event_type", "manual")
        players: list[dict[str, Any]] | None = body.get("players")

        if not isinstance(players, list):
            return jsonify({"error": "players must be a list"}), 400

        if event_type not in ("manual", "sync"):
            return jsonify({"error": "event_type must be 'manual' or 'sync'"}), 400

        if parent_id is not None and type(parent_id) is not int:
            return jsonify({"error": "parent_id must be an integer or null"}), 400

        # Validate parent exists if provided
        if parent_id is not None:
            parent_row = conn.execute(
                "SELECT source FROM snapshots WHERE id = ?", (parent_id,)
            ).fetchone()
            if not parent_row:
                return jsonify({"error": "parent snapshot not found"}), 404

            # Check if parent is a leaf node (has no children)
            has_children = conn.execute(
                "SELECT 1 FROM events WHERE source_snapshot_id = ? LIMIT 1",
                (parent_id,)
            ).fetchone() is not None

            # If parent is a leaf node, update in-place
            if not has_children:
                # Bypass STRICT GUARD for consecutive syncs on leaf nodes
                # (it is perfectly safe and desirable to update a leaf sync in-place)
                
                # Update the snapshot source
                source = "notion_sync" if event_type == "sync" else "manual"
                conn.execute(
                    "UPDATE snapshots SET source = ? WHERE id = ?",
                    (source, parent_id)
                )

                # Clear old roster
                conn.execute(
                    "DELETE FROM snapshot_players WHERE snapshot_id = ?",
                    (parent_id,)
                )

                # Insert new players
                for player in players:
                    nombre = player.get("nombre", "")
                    if not nombre:
                        continue
                    player_id = db.get_or_create_player(conn, nombre)
                    db.add_snapshot_player(
                        conn, parent_id, player_id,
                        player.get("experiencia", "Nuevo"),
                        int(player.get("juegos_este_ano", 0)),
                        int(player.get("prioridad", 0)),
                        int(player.get("partidas_deseadas", 1)),
                        int(player.get("partidas_gm", 0)),
                    )

                conn.commit()
                return jsonify({"snapshot_id": parent_id})

            # If parent is an internal node (has children), apply STRICT GUARD
            if event_type == "sync" and parent_row["source"] == "notion_sync":
                return jsonify({"error": "El snapshot base ya fue generado por notion_sync y aún no se ha jugado una partida."}), 400

        # Create snapshot with appropriate source (for internal nodes or no parent)
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


@app.route("/api/game/draft", methods=["POST"])
def api_game_draft():
    """
    Generates a draft of game tables without saving to the database.
    Input: {"snapshot_id": int}
    Returns: ResultadoPartidas.to_dict()
    """
    conn = db.get_db()
    try:
        data = request.get_json()
        snapshot_id = data.get("snapshot_id")
        if not snapshot_id:
            return jsonify({"error": "snapshot_id is required"}), 400

        rows = db.get_snapshot_players(conn, snapshot_id)
        jugadores = [
            Jugador(
                r["nombre"], r["experiencia"], r["juegos_este_ano"],
                str(bool(r["prioridad"])), r["partidas_deseadas"], r["partidas_gm"],
                r["c_england"], r["c_france"], r["c_germany"], r["c_italy"],
                r["c_austria"], r["c_russia"], r["c_turkey"]
            )
            for r in rows
        ]

        # Check for duplicates
        from collections import Counter
        duplicates = [n for n, c in Counter(j.nombre for j in jugadores).items() if c > 1]
        if duplicates:
            return jsonify({"error": f"Nombres duplicados en el snapshot: {', '.join(duplicates)}"}), 400

        resultado = calcular_partidas(jugadores)
        if not resultado:
            return jsonify({"error": "No hay suficientes jugadores para armar una partida."}), 400

        return jsonify(resultado.to_dict())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/api/game/save", methods=["POST"])
def api_game_save():
    """
    Saves a confirmed game draft to the database.
    Input: {"snapshot_id": int, "draft": dict}
    Returns: {"game_id": int}
    """
    conn = db.get_db()
    try:
        data = request.get_json()
        snapshot_id = data.get("snapshot_id")
        draft = data.get("draft")
        if not snapshot_id or not draft:
            return jsonify({"error": "snapshot_id and draft are required"}), 400

        game_id = save_game_draft(conn, snapshot_id, draft)
        conn.commit()
        return jsonify({"game_id": game_id})
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/api/run/<script>", methods=["POST"])
def api_run(script: str):
    if script not in ("notion_sync",):
        return jsonify({"error": "unknown script"}), 400

    cwd = PROJECT_ROOT  # project root, so -m backend.X works
    body: dict[str, Any] = request.get_json(silent=True) or {}
    snapshot_id: int | None = body.get("snapshot")

    # notion_sync allows empty snapshot_id (first-time sync exception handled in notion_sync.py)
    if snapshot_id is not None and type(snapshot_id) is not int:
        return jsonify({"error": "snapshot must be an integer"}), 400

    SCRIPT_MODULES = {"notion_sync": "backend.sync.notion_sync"}
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
        body: dict[str, Any] = request.get_json(silent=True) or {}
        old_name: str | None = body.get("old_name")
        new_name: str | None = body.get("new_name")
        
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
        
        body: dict[str, Any] = request.get_json(silent=True) or {}
        nombre: str | None = body.get("nombre")
        if not nombre:
            return jsonify({"error": "nombre is required"}), 400
        
        experiencia: str = body.get("experiencia", "Nuevo")
        juegos_este_ano: int = int(body.get("juegos_este_ano", 0))
        prioridad: int = int(body.get("prioridad", 0))
        partidas_deseadas: int = int(body.get("partidas_deseadas", 1))
        partidas_gm: int = int(body.get("partidas_gm", 0))
        
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
    start_background_sync()
    threading.Timer(0.8, lambda: webbrowser.open("http://127.0.0.1:5001")).start()
    app.run(debug=False, port=5001)


if __name__ == "__main__":
    main()
