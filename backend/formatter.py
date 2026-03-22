"""
formatter.py – Pure text generation for game results.

All functions return strings or lists of strings. No file I/O.

Functions:
  _formatear_copypaste   → share-ready text; stored in game_events.copypaste_text
  _formatear_resultado   → detailed event results for terminal output
  _construir_proyeccion  → per-player Juegos_Este_Ano projection table
"""
from __future__ import annotations

from collections import Counter

from .models import Mesa, ResultadoPartidas

SEP: str = "─" * 44


# ── Share section ──────────────────────────────────────────────────────────────

def _formatear_copypaste(resultado: ResultadoPartidas) -> str:
    """
    Section ready to copy-paste (WhatsApp, Discord, etc.).
    Names only — no experience metadata or decorations.
    """
    lineas: list[str] = []
    for mesa in resultado.mesas:
        gm_str: str = f"  |  GM: {mesa.gm.nombre}" if mesa.gm else ""
        lineas.append(f"Partida {mesa.numero}{gm_str}")
        for i, jugador in enumerate(mesa.jugadores):
            lineas.append(f"  {i + 1}. {jugador.nombre}")
        lineas.append("")
    if resultado.tickets_sobrantes:
        lineas.append("Lista de espera:")
        vistos: set[str] = set()
        for j in resultado.tickets_sobrantes:
            if j.nombre not in vistos:
                vistos.add(j.nombre)
                lineas.append(f"  - {j.nombre}")
    return "\n".join(lineas)


# ── Detail section ─────────────────────────────────────────────────────────────

def _formatear_resultado(
    resultado: ResultadoPartidas,
    sep: str = SEP,
) -> list[str]:
    """Returns lines for the DETALLE DEL EVENTO section."""
    lineas: list[str] = [
        f"  SE GENERARON {len(resultado.mesas)} PARTIDA(S)",
        sep,
    ]

    for mesa in resultado.mesas:
        nuevos: int = sum(1 for j in mesa.jugadores if j.es_nuevo)
        antiguos: int = sum(1 for j in mesa.jugadores if not j.es_nuevo)
        gm_str: str = f"GM: {mesa.gm.nombre}" if mesa.gm else "⚠️  Sin GM asignado"
        lineas.append(f"\n[ Partida {mesa.numero} ]  Nuevos: {nuevos}  Antiguos: {antiguos}  {gm_str}")
        for j, jugador in enumerate(mesa.jugadores):
            etiqueta: str = "Nuevo" if jugador.es_nuevo else f"Antiguo ({jugador.juegos_ano} juegos)"
            lineas.append(f"  {j + 1}. {jugador.nombre}  —  {etiqueta}")

    # Unique GMs who referee at least one table, in order of appearance
    gms_vistos: set[str] = set()
    gms_activos: list = []
    for mesa in resultado.mesas:
        if mesa.gm and mesa.gm.nombre not in gms_vistos:
            gms_vistos.add(mesa.gm.nombre)
            gms_activos.append(mesa.gm)

    if gms_activos:
        lineas += [f"\n{sep}", "  GAME MASTERS", sep]
        for gm in gms_activos:
            mesas_del_gm: list[Mesa] = [
                m for m in resultado.mesas if m.gm and m.gm.nombre == gm.nombre
            ]
            mesas_str: str = ", ".join(f"Partida {m.numero}" for m in mesas_del_gm)
            mesas_como_jugador: int = sum(
                1 for m in resultado.mesas
                if any(j is gm for j in m.jugadores)
            )
            lineas.append(
                f"  {gm.nombre}: arbitra {mesas_str}  "
                f"(quería jugar {gm.partidas_deseadas}, jugará {mesas_como_jugador})"
            )

    if resultado.tickets_sobrantes:
        lineas += [f"\n{sep}", "  JUGADORES EN LISTA DE ESPERA", sep]
        conteo: Counter[str] = Counter(t.nombre for t in resultado.tickets_sobrantes)
        for nombre, cupos in conteo.items():
            sufijo = f"{cupos} cupo(s) sin asignar" if cupos > 1 else "1 cupo sin asignar"
            lineas.append(f"  - {nombre}  ({sufijo})")

    return lineas


# ── Projection section ─────────────────────────────────────────────────────────

def _construir_proyeccion(
    resultado: ResultadoPartidas,
    jugadores: list,
) -> list[str]:
    """
    Projects each player's Juegos_Este_Ano after this event.

    Counts:
      +1 per table played as a player.
      +0 for GMing (GMing does not add to Juegos_Este_Ano; the role is
           reflected in the algorithm's weight system with a 0.5 factor).
    """
    cupos_jugados: Counter[str] = Counter(
        j.nombre for mesa in resultado.mesas for j in mesa.jugadores
    )
    cupos_gm: Counter[str] = Counter(
        mesa.gm.nombre for mesa in resultado.mesas if mesa.gm is not None
    )

    filas: list[tuple[int, str, int, int, int, int]] = []
    for jugador in jugadores:
        jugadas: int = cupos_jugados[jugador.nombre]
        como_gm: int = cupos_gm[jugador.nombre]
        actual: int = jugador.juegos_ano
        proyectado: int = actual + jugadas
        filas.append((proyectado, jugador.nombre, actual, jugadas, como_gm, proyectado))

    filas.sort(key=lambda r: (-r[0], r[1]))

    ancho: int = max(len(r[1]) for r in filas)
    enc: str = f"  {'Jugador':{ancho}}  Actual  +Juega  +GM  Proyectado"
    lineas: list[str] = [enc, "  " + "-" * (len(enc) - 2)]
    for _, nombre, actual, jugadas, como_gm, proyectado in filas:
        lineas.append(
            f"  {nombre:{ancho}}    {actual:>3}     {jugadas:>3}   {como_gm:>2}         {proyectado:>3}"
        )

    return lineas


