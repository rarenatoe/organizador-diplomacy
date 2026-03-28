"""
persistence.py – Game-event persistence logic for draft saving.
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

from backend.db import db, db_game

from .formatter import formatear_copypaste_from_dict


def save_game_draft(
    conn: sqlite3.Connection,
    input_snapshot_id: int,
    draft_data: dict[str, Any]
) -> int:
    """
    Saves a confirmed game draft to the database.
    Creates:
      - output snapshot (updated stats)
      - game_event
      - mesas, mesa_players, and waiting_list entries

    Returns the new game_event_id. Does NOT commit.
    """
    # 1. Create the output snapshot based on the draft results
    # We need to adapt draft_data to what create_output_snapshot_from_draft expects
    out_id = create_output_snapshot_from_draft(conn, input_snapshot_id, draft_data)

    # 2. Format copypaste text
    copypaste = formatear_copypaste_from_dict(draft_data)

    # 3. Create the game event
    intentos = draft_data.get("intentos_usados", 0)
    ge_id = db_game.create_game_event(conn, input_snapshot_id, out_id, intentos, copypaste)

    # 4. Create mesas and mesa_players
    for mesa in draft_data.get("mesas", []):
        gm_pid: int | None = None
        gm_nombre = mesa.get("gm", {}).get("nombre") if mesa.get("gm") else None
        if gm_nombre:
            gm_pid = db.get_or_create_player(conn, gm_nombre)
        
        mesa_id = db_game.create_mesa(conn, ge_id, mesa["numero"], gm_pid)
        for orden, jugador in enumerate(mesa.get("jugadores", []), start=1):
            pid = db.get_or_create_player(conn, jugador["nombre"])
            db_game.add_mesa_player(conn, mesa_id, pid, orden, jugador.get("pais"))

    # 5. Create waiting list
    waiting_players = draft_data.get("tickets_sobrantes", [])
    conteo_espera: Counter[str] = Counter(j["nombre"] for j in waiting_players)
    
    for orden, (nombre, cupos) in enumerate(conteo_espera.items(), start=1):
        pid = db.get_or_create_player(conn, nombre)
        db_game.add_waiting_player(conn, ge_id, pid, orden, cupos)

    return ge_id

def create_output_snapshot_from_draft(
    conn: sqlite3.Connection,
    input_snapshot_id: int,
    draft_data: dict[str, Any]
) -> int:
    """
    Creates the post-game snapshot based on draft data.
    """
    cupos_jugados: Counter[str] = Counter()
    for mesa in draft_data.get("mesas", []):
        for j in mesa.get("jugadores", []):
            cupos_jugados[j["nombre"]] += 1
            
    nombres_en_espera: set[str] = {j["nombre"] for j in draft_data.get("tickets_sobrantes", [])}

    snap_id = db.create_snapshot(conn, "organizar")

    for p in db.get_snapshot_players(conn, input_snapshot_id):
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0
        pid = conn.execute(
            "SELECT id FROM players WHERE nombre = ?", (nombre,)
        ).fetchone()["id"]
        
        db.add_snapshot_player(
            conn, snap_id, pid,
            "Antiguo" if fue_promovido else p["experiencia"],
            p["juegos_este_ano"] + jugadas,
            1 if nombre in nombres_en_espera else 0,
            p["partidas_deseadas"],
            0,  # partidas_gm reset
        )

    return snap_id


def update_game_draft(
    conn: sqlite3.Connection,
    game_id: int,
    input_snapshot_id: int,
    output_snapshot_id: int,
    draft_data: dict[str, Any]
) -> int:
    """
    Updates an existing game draft in place.
    
    Updates:
      - game_details (intentos/copypaste) in place
      - DELETEs from mesas and waiting_list where event_id = game_id
      - DELETEs output_snapshot_id roster and re-inserts it using create_output_snapshot_from_draft logic
      - re-inserts mesas/waiting_list using save_game_draft logic
    
    Returns the game_id. Does NOT commit.
    """
    # 1. Update game_details in place
    copypaste = formatear_copypaste_from_dict(draft_data)
    intentos = draft_data.get("intentos_usados", 0)
    
    conn.execute(
        "UPDATE game_details SET intentos = ?, copypaste_text = ? WHERE event_id = ?",
        (intentos, copypaste, game_id)
    )
    
    # 2. Delete existing mesas and waiting_list for this game
    conn.execute("DELETE FROM mesa_players WHERE mesa_id IN (SELECT id FROM mesas WHERE event_id = ?)", (game_id,))
    conn.execute("DELETE FROM mesas WHERE event_id = ?", (game_id,))
    conn.execute("DELETE FROM waiting_list WHERE event_id = ?", (game_id,))
    
    # 3. Delete output snapshot roster and re-insert using create_output_snapshot_from_draft logic
    conn.execute("DELETE FROM snapshot_players WHERE snapshot_id = ?", (output_snapshot_id,))
    
    # Re-create the output snapshot with updated player data
    cupos_jugados: Counter[str] = Counter()
    for mesa in draft_data.get("mesas", []):
        for j in mesa.get("jugadores", []):
            cupos_jugados[j["nombre"]] += 1
            
    nombres_en_espera: set[str] = {j["nombre"] for j in draft_data.get("tickets_sobrantes", [])}

    for p in db.get_snapshot_players(conn, input_snapshot_id):
        nombre = p["nombre"]
        jugadas = cupos_jugados[nombre]
        fue_promovido = p["experiencia"] == "Nuevo" and jugadas > 0
        pid = conn.execute(
            "SELECT id FROM players WHERE nombre = ?", (nombre,)
        ).fetchone()["id"]
        
        db.add_snapshot_player(
            conn, output_snapshot_id, pid,
            "Antiguo" if fue_promovido else p["experiencia"],
            p["juegos_este_ano"] + jugadas,
            1 if nombre in nombres_en_espera else 0,
            p["partidas_deseadas"],
            0,  # partidas_gm reset
        )
    
    # 4. Re-insert mesas and waiting_list using save_game_draft logic
    for mesa in draft_data.get("mesas", []):
        gm_pid: int | None = None
        gm_nombre = mesa.get("gm", {}).get("nombre") if mesa.get("gm") else None
        if gm_nombre:
            gm_pid = db.get_or_create_player(conn, gm_nombre)
        
        mesa_id = db_game.create_mesa(conn, game_id, mesa["numero"], gm_pid)
        for orden, jugador in enumerate(mesa.get("jugadores", []), start=1):
            pid = db.get_or_create_player(conn, jugador["nombre"])
            db_game.add_mesa_player(conn, mesa_id, pid, orden, jugador.get("pais"))

    # 5. Create waiting list
    waiting_players = draft_data.get("tickets_sobrantes", [])
    conteo_espera: Counter[str] = Counter(j["nombre"] for j in waiting_players)
    
    for orden, (nombre, cupos) in enumerate(conteo_espera.items(), start=1):
        pid = db.get_or_create_player(conn, nombre)
        db_game.add_waiting_player(conn, game_id, pid, orden, cupos)

    return game_id
