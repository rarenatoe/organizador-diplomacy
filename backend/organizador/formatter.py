"""
formatter.py – Pure text generation for game results.

All functions return strings or lists of strings. No file I/O.

Functions:
  formatear_copypaste           → share-ready text; stored in game_events.copypaste_text
  formatear_resultado           → detailed event results for terminal output
  construir_proyeccion          → per-player Juegos_Este_Ano projection table
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Jugador, Mesa, ResultadoPartidas

SEP: str = "─" * 44

# Country name translations from English to Spanish
_COUNTRY_TRANSLATIONS: dict[str, str] = {
    "England": "Inglaterra",
    "France": "Francia", 
    "Germany": "Alemania",
    "Italy": "Italia",
    "Austria": "Austria",
    "Russia": "Rusia",
    "Turkey": "Turquía"
}

def translate_country(pais: str) -> str:
    """Translate English country name to Spanish."""
    if not pais or pais == "":
        return ""
    return _COUNTRY_TRANSLATIONS.get(pais, pais)


# ── Share section ──────────────────────────────────────────────────────────────

def formatear_copypaste(resultado: ResultadoPartidas) -> str:
    """
    Section ready to copy-paste (WhatsApp, Discord, etc.).
    Names only — no experience metadata or decorations.
    """
    return formatear_copypaste_from_dict(resultado.model_dump())


def formatear_copypaste_from_dict(resultado_dict: dict[str, Any]) -> str:
    """
    Section ready to copy-paste from a dictionary representation.
    """
    lineas: list[str] = []
    for mesa in resultado_dict.get("mesas", []):
        gm_nombre = mesa.get("gm", {}).get("nombre") if mesa.get("gm") else None
        gm_str: str = f"  |  GM: {gm_nombre}" if gm_nombre else ""
        lineas.append(f"Partida {mesa['numero']}{gm_str}")
        for i, jugador in enumerate(mesa.get("jugadores", [])):
            pais_str = f" ({translate_country(jugador.get('pais'))})" if jugador.get('pais') else ""
            lineas.append(f"  {i + 1}. {jugador['nombre']}{pais_str}")
        lineas.append("")
    
    sobrantes = resultado_dict.get("tickets_sobrantes", [])
    if sobrantes:
        lineas.append("Lista de espera:")
        vistos: set[str] = set()
        for j in sobrantes:
            nombre = j["nombre"]
            if nombre not in vistos:
                vistos.add(nombre)
                lineas.append(f"  - {nombre}")
    return "\n".join(lineas)


# ── Detail section ─────────────────────────────────────────────────────────────

def formatear_resultado(
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
            pais_str = f" ({translate_country(jugador.pais)})" if jugador.pais else ""
            etiqueta: str = "Nuevo" if jugador.es_nuevo else f"Antiguo ({jugador.juegos_ano} juegos)"
            lineas.append(f"  {j + 1}. {jugador.nombre}{pais_str}  —  {etiqueta}")

    # Unique GMs who referee at least one table, in order of appearance
    gms_vistos: set[str] = set()
    gms_activos: list[Jugador] = []
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

def construir_proyeccion(
    resultado: ResultadoPartidas,
    jugadores: list[Jugador],
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
        actual: int = int(jugador.juegos_ano)
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


