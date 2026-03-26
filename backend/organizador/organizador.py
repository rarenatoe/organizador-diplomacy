from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

from backend.config import DATA_DIR
from backend.db import db, db_game

from .formatter import (
    _construir_proyeccion,
    _formatear_copypaste,
    _formatear_resultado,
)
from .models import Jugador, Mesa, ResultadoPartidas

SEP: str = "─" * 44


def _calcular_partidas(jugadores: list[Jugador]) -> ResultadoPartidas | None:
    """
    Núcleo del algoritmo. Devuelve un ResultadoPartidas, o None si no hay
    suficientes jugadores para armar una partida.
    Lanza ValueError si la configuración de GMs es inválida.

    Ejecuta hasta MAX_INTENTOS distribuciones aleatorias y devuelve la que
    deja el menor número de jugadores en lista de espera. El mínimo teórico
    (tickets que no caben en ningún escenario) se calcula una sola vez y
    se usa como condición de parada temprana.
    """
    MAX_INTENTOS: int = 200

    # ── Cálculo determinístico (se hace una sola vez) ─────────────────────────

    total_tickets_brutos: int = sum(j.partidas_deseadas for j in jugadores)
    mesas_estimadas: int = total_tickets_brutos // 7

    if mesas_estimadas == 0:
        return None

    # Cada mesa acepta exactamente un GM.
    total_slots_gm: int = sum(j.partidas_gm for j in jugadores)
    if total_slots_gm > mesas_estimadas:
        raise ValueError(
            f"Hay {total_slots_gm} slot(s) de GM pero solo {mesas_estimadas} "
            f"partida(s). Cada mesa acepta un único GM."
        )

    # Cupos reales de juego: GMs descontados, sin mutar los objetos Jugador.
    jugables: dict[str, int] = {
        jugador.nombre: (
            min(jugador.partidas_deseadas, mesas_estimadas - jugador.partidas_gm)
            if jugador.partidas_gm > 0
            else jugador.partidas_deseadas
        )
        for jugador in jugadores
    }

    # GMs ordenados: los que arbitran más mesas reciben su asignación primero.
    gms_activos: list[Jugador] = sorted(
        [j for j in jugadores if j.partidas_gm > 0],
        key=lambda j: j.partidas_gm,
        reverse=True,
    )

    # Tickets con peso de participación (pesos determinísticos).
    #
    #   weight_after = gm_weight + slot_index + jugador.puntaje_prioridad
    #
    #   gm_weight         = partidas_gm × 0.5
    #   slot_index        = 1.0 para 1er cupo, 2.0 para 2do, etc.
    #   puntaje_prioridad = fracción continua [0.00, 0.90]
    #
    # Invariantes:
    #   • Primeros slots [1.00, 1.90] < segundos slots [2.00, 2.90] →
    #     nadie queda con 0 participaciones mientras hay cupo.
    #   • Dentro del mismo slot, menos juegos → menor peso → entra antes.
    weighted_tickets: list[tuple[float, Jugador]] = []
    for jugador in jugadores:
        gm_weight: float = jugador.partidas_gm * 0.5
        priority_fraction: float = jugador.puntaje_prioridad
        for i in range(jugables[jugador.nombre]):
            weight_after: float = gm_weight + float(i + 1) + priority_fraction
            weighted_tickets.append((weight_after, jugador))

    mesas_reales: int = len(weighted_tickets) // 7

    if mesas_reales == 0:
        return None

    # Piso de la lista de espera: tickets que no caben en ningún escenario.
    minimo_teorico: int = len(weighted_tickets) - mesas_reales * 7

    # ── distribuir_tickets: definida una vez, recibe contexto por parámetro ───

    def distribuir_tickets(
        lista_tickets: list[tuple[float, Jugador]],
        es_grupo_nuevo: bool,
        partidas: list[list[Jugador]],
        gm_bloqueados: dict[str, set[int]],
    ) -> list[Jugador]:
        # Más restringidos primero (GMs bloqueados en varias mesas tienen
        # menos opciones; procesarlos antes evita que otros llenen su única
        # mesa válida). Desempate por weight_after.
        lista_tickets.sort(
            key=lambda t: (
                -len(gm_bloqueados.get(t[1].nombre, set())),
                t[0],
            )
        )
        rechazados: list[Jugador] = []
        for _weight, ticket in lista_tickets:
            bloqueados: set[int] = gm_bloqueados.get(ticket.nombre, set())
            partidas_validas: list[list[Jugador]] = [
                p
                for i, p in enumerate(partidas)
                if len(p) < 7
                and not any(j.nombre == ticket.nombre for j in p)
                and i not in bloqueados
            ]
            if not partidas_validas:
                rechazados.append(ticket)
                continue
            random.shuffle(partidas_validas)
            if es_grupo_nuevo:
                partidas_validas.sort(key=lambda p: (sum(1 for j in p if j.es_nuevo), len(p)))
            else:
                partidas_validas.sort(key=lambda p: (sum(1 for j in p if not j.es_nuevo), len(p)))
            partidas_validas[0].append(ticket)
        return rechazados

    # ── Reintentos: conservar la distribución con menor lista de espera ───────

    intentos: int = 0
    mejor: ResultadoPartidas | None = None

    for _ in range(MAX_INTENTOS):
        intentos += 1

        # Asignación aleatoria de mesas a GMs
        indices_gm_pool: list[int] = list(range(mesas_estimadas))
        random.shuffle(indices_gm_pool)

        gm_indices: dict[str, list[int]] = {}
        ptr: int = 0
        for gm in gms_activos:
            gm_indices[gm.nombre] = indices_gm_pool[ptr : ptr + gm.partidas_gm]
            ptr += gm.partidas_gm

        gm_bloqueados: dict[str, set[int]] = {
            nombre: set(indices) for nombre, indices in gm_indices.items()
        }

        # Mezcla aleatoria para desempatar tickets con el mismo peso
        tickets_iter: list[tuple[float, Jugador]] = list(weighted_tickets)
        random.shuffle(tickets_iter)
        tickets_iter.sort(key=lambda t: t[0])

        tickets_aceptados = tickets_iter[: mesas_reales * 7]
        sobrantes_iniciales: list[Jugador] = [j for _, j in tickets_iter[mesas_reales * 7 :]]

        tickets_nuevos: list[tuple[float, Jugador]] = [
            (w, j) for w, j in tickets_aceptados if j.es_nuevo
        ]
        tickets_antiguos: list[tuple[float, Jugador]] = [
            (w, j) for w, j in tickets_aceptados if not j.es_nuevo
        ]

        partidas: list[list[Jugador]] = [[] for _ in range(mesas_reales)]

        rechazados_nuevos = distribuir_tickets(tickets_nuevos, True, partidas, gm_bloqueados)
        rechazados_antiguos = distribuir_tickets(tickets_antiguos, False, partidas, gm_bloqueados)
        tickets_sobrantes = sobrantes_iniciales + rechazados_nuevos + rechazados_antiguos

        # Construir mesas semánticas para este intento
        mesa_a_gm: dict[int, Jugador] = {}
        for nombre, indices in gm_indices.items():
            gm_obj: Jugador = next(j for j in jugadores if j.nombre == nombre)
            for idx in indices:
                if idx < mesas_reales:
                    mesa_a_gm[idx] = gm_obj

        mesas: list[Mesa] = [
            Mesa(numero=i + 1, jugadores=partidas[i], gm=mesa_a_gm.get(i))
            for i in range(mesas_reales)
        ]

        resultado = ResultadoPartidas(
            mesas=mesas,
            tickets_sobrantes=tickets_sobrantes,
            minimo_teorico=minimo_teorico,
        )

        if mejor is None or len(resultado.tickets_sobrantes) < len(mejor.tickets_sobrantes):
            mejor = resultado

        if len(mejor.tickets_sobrantes) == minimo_teorico:
            break  # No se puede mejorar más; detener temprano

    if mejor is not None:
        mejor.intentos_usados = intentos

    return mejor



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
    conn = db.get_db(db.DB_PATH if directorio == DATA_DIR else directorio / "diplomacy.db")

    # ── Validate snapshot ────────────────────────────────────────────────────
    if snapshot_id is None:
        print("❌  snapshot_id es requerido para operaciones de branching.", file=sys.stderr)
        conn.close()
        return

    # ── Build Jugador objects ───────────────────────────────────────────
    rows = db.get_snapshot_players(conn, snapshot_id)
    jugadores: list[Jugador] = [
        Jugador(
            r["nombre"], r["experiencia"], r["juegos_este_ano"],
            str(bool(r["prioridad"])), r["partidas_deseadas"], r["partidas_gm"],
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
        resultado: ResultadoPartidas | None = _calcular_partidas(jugadores)
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
    copypaste = _formatear_copypaste(resultado)
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
                db_game.add_mesa_player(conn, mesa_id, pid, orden)

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
    for line in _formatear_resultado(resultado):
        print(line)
    print()
    for line in _construir_proyeccion(resultado, jugadores):
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
