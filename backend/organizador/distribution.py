from __future__ import annotations

import random
from .models import Jugador, Mesa, ResultadoPartidas

# ── Distribution Logic ───────────────────────────────────────────────────────

def distribuir_tickets(
    lista_tickets: list[tuple[float, Jugador]],
    es_grupo_nuevo: bool,
    partidas: list[list[Jugador]],
    gm_bloqueados: dict[str, set[int]],
) -> list[Jugador]:
    """
    Distributes tickets into tables, respecting GM constraints and priority.
    """
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


def run_distribution_loop(
    jugadores: list[Jugador],
    weighted_tickets: list[tuple[float, Jugador]],
    gms_activos: list[Jugador],
    mesas_estimadas: int,
    mesas_reales: int,
    minimo_teorico: int,
    max_intentos: int = 200,
) -> ResultadoPartidas | None:
    """
    Runs the random distribution retry loop to find the best table arrangement.
    """
    intentos: int = 0
    mejor: ResultadoPartidas | None = None

    for _ in range(max_intentos):
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
