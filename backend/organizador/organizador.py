from __future__ import annotations

import sys
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from backend.config import DATA_DIR
from backend.db import db, db_game

from .core import calcular_partidas
from .formatter import (
    construir_proyeccion,
    formatear_copypaste,
    formatear_resultado,
)
from .models import Jugador, ResultadoPartidas

SEP: str = "─" * 44


def organizar_partidas(
    snapshot_id: int | None = None,
    directorio: Path = DATA_DIR,
) -> None:
    """
    Organiza una ronda de partidas.

    Reads player data from the database, runs the algorithm, and persists
    all results atomically:
      - output snapshot (updated juegos_este_ano + prioridad)
      - game_event with copypaste_text
      - mesas, mesa_players, waiting_list

    snapshot_id is required — no default to latest.
    """
    db_path = str(db.DB_PATH if directorio == DATA_DIR else directorio / "diplomacy.db")
    conn = db.get_db(db_path)

    # ── Validate snapshot ────────────────────────────────────────────────────
    if snapshot_id is None:
        print("❌  snapshot_id es requerido para operaciones de branching.", file=sys.stderr)
        conn.close()
        return

    # ── Build Jugador objects ───────────────────────────────────────────
    rows = db.get_snapshot_players(conn, snapshot_id)
    jugadores: list[Jugador] = [
        Jugador(
            nombre=r["nombre"],
            experiencia=r["experiencia"],
            juegos_ano=r["juegos_este_ano"],
            prioridad=str(bool(r["prioridad"])),
            partidas_deseadas=r["partidas_deseadas"],
            partidas_gm=r["partidas_gm"],
        )
        for r in rows
    ]

    # ── Validate unique names ───────────────────────────────────────────
    duplicates = [n for n, c in Counter(j.nombre for j in jugadores).items() if c > 1]
    if duplicates:
        print(f"⚠️  Nombres duplicados en snapshot #{snapshot_id}: {', '.join(duplicates)}")
        conn.close()
        return

    try:
        resultado: ResultadoPartidas | None = calcular_partidas(jugadores)
    except ValueError as e:
        print(f"⚠️  Error de configuración: {e}")
        conn.close()
        return

    if resultado is None:
        print("No hay suficientes jugadores para armar ni siquiera una partida de 7.")
        conn.close()
        return

    # ── Compute summary stats before writing ──────────────────────────────
    cupos_post: Counter[str] = Counter(
        j.nombre for mesa in resultado.mesas for j in mesa.jugadores
    )
    promovidos = [j.nombre for j in jugadores if j.es_nuevo and cupos_post[j.nombre] > 0]
    vistos: set[str] = set()
    en_espera_unicos: list[str] = []
    for j in resultado.tickets_sobrantes:
        if j.nombre not in vistos:
            vistos.add(j.nombre)
            en_espera_unicos.append(j.nombre)
    total_cupos  = len(resultado.mesas) * 7
    total_tickets = total_cupos + resultado.minimo_teorico

    # ── Persist everything in a single transaction ──────────────────────────
    copypaste = formatear_copypaste(resultado)
    try:
        out_id = db_game.create_output_snapshot(conn, snapshot_id, resultado)
        ge_id  = db_game.create_game_event(
            conn, snapshot_id, out_id,
            resultado.intentos_usados, copypaste,
        )
        for mesa in resultado.mesas:
            gm_pid: int | None = None
            if mesa.gm:
                gm_pid = db.get_or_create_player(conn, mesa.gm.nombre)
            mesa_id = db_game.create_mesa(conn, ge_id, mesa.numero, gm_pid)
            for orden, jugador in enumerate(mesa.jugadores, start=1):
                pid = db.get_or_create_player(conn, jugador.nombre)
                db_game.add_mesa_player(conn, mesa_id, pid, orden, jugador.pais or None)

        conteo_espera: Counter[str] = Counter(
            j.nombre for j in resultado.tickets_sobrantes
        )
        for orden, (nombre, cupos) in enumerate(conteo_espera.items(), start=1):
            pid = db.get_or_create_player(conn, nombre)
            db_game.add_waiting_player(conn, ge_id, pid, orden, cupos)

        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()

    # ── Console summary ────────────────────────────────────────────────────
    print(
        f"\n✓  {len(resultado.mesas)} partidas  |  "
        f"{total_tickets} solicitados, {total_cupos} disponibles, "
        f"{len(en_espera_unicos)} en espera  |  {resultado.intentos_usados} intento(s)"
    )
    print(f"✓  Evento #{ge_id} guardado  (snapshot #{snapshot_id} → #{out_id})")
    if promovidos:
        print(f"   Promovidos:  {', '.join(promovidos)}")
    if en_espera_unicos:
        print(f"   En espera:   {', '.join(en_espera_unicos)}")
    print()
    for line in formatear_resultado(resultado):
        print(line)
    print()
    for line in construir_proyeccion(resultado, jugadores):
        print(line)


if __name__ == "__main__":
    import argparse as _ap
    _parser = _ap.ArgumentParser(description="Organiza las partidas de Diplomacy")
    _parser.add_argument(
        "--snapshot", metavar="ID", type=int,
        help="ID del snapshot de origen (por defecto: el último)",
    )
    _args = _parser.parse_args()
    organizar_partidas(snapshot_id=_args.snapshot)
