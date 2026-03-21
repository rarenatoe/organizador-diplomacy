from __future__ import annotations
import csv
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from utils import siguiente_csv, ultimo_csv

from utils import DIRECTORIO, siguiente_csv, ultimo_csv

SEP: str = "─" * 44

# ─────────────────────────────────────────────────────────────────────────────
# Formato de jugadores.csv:
#   Nombre            – nombre del jugador
#   Experiencia       – "Nuevo" o "Antiguo"
#   Juegos_Este_Ano   – entero (partidas jugadas este año)
#   Prioridad         – "True" / "False" (jugador con prioridad especial)
#   Partidas_Deseadas – entero (cuántas partidas quiere jugar)
#   Partidas_GM       – entero (en cuántas partidas será Game Master;
#                       0 = no es GM. El algoritmo asigna automáticamente
#                       qué mesa(s) le corresponden.)
# ─────────────────────────────────────────────────────────────────────────────

class Jugador:
    def __init__(
        self,
        nombre: str,
        experiencia: str,
        juegos_ano: str | int,
        prioridad: str,
        partidas_deseadas: str | int,
        partidas_gm: str | int = 0,
    ) -> None:
        self.nombre: str = nombre
        self.es_nuevo: bool = (experiencia.strip().lower() == "nuevo")
        self.juegos_ano: int = int(juegos_ano)
        self.tiene_prioridad: bool = (prioridad.strip().lower() == "true")
        self.partidas_deseadas: int = int(partidas_deseadas)
        # Cuántas partidas arbitrará como Game Master (0 = no es GM).
        # El algoritmo asigna automáticamente qué mesa(s) específica(s) le tocan.
        self.partidas_gm: int = int(partidas_gm)

    @property
    def puntaje_prioridad(self) -> float:
        """
        Fracción de prioridad continua usada en weight_after. Menor = mayor prioridad.

        Escala:
          0.00  → nuevo o con prioridad especial
          0.05  → antiguo, 0 partidas este año
          0.20  → antiguo, 1 partida este año
          0.35  → antiguo, 2 partidas este año
          0.50  → antiguo, 3 partidas este año
           ⋮    0.05 + juegos_ano × 0.15, máximo 0.90

        El step de 0.15 por partida (vs 0.10 anterior) hace que la liga se equilibre
        más rápido: alguien con 4 partidas (0.65) cede claramente ante alguien con 0 (0.05).
        """
        if self.es_nuevo or self.tiene_prioridad:
            return 0.0
        return min(0.05 + self.juegos_ano * 0.15, 0.90)


@dataclass
class Mesa:
    """Una partida con sus jugadores y su Game Master (si tiene)."""
    numero: int               # 1-based, para display
    jugadores: list[Jugador]
    gm: Jugador | None = None


@dataclass
class ResultadoPartidas:
    """Resultado tipado del algoritmo. Acceso por atributo en lugar de claves de dict."""
    mesas: list[Mesa]
    tickets_sobrantes: list[Jugador]
    minimo_teorico: int = 0   # tickets que no caben en ningún escenario posible
    intentos_usados: int = 0  # iteraciones del bucle de reintentos


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


def _formatear_copypaste(resultado: ResultadoPartidas) -> list[str]:
    """
    Sección lista para copiar y pegar (WhatsApp, Discord, etc.).
    Solo nombres — sin metadatos de experiencia ni decoraciones.
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
    return lineas


def _formatear_resultado(
    resultado: ResultadoPartidas,
    sep: str = SEP,
) -> list[str]:
    """Devuelve las líneas de texto del resultado de partidas (sin proyección)."""
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

    # GMs únicos que arbitran al menos una mesa, en orden de aparición
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


def _construir_proyeccion(
    resultado: ResultadoPartidas,
    jugadores: list[Jugador],
    sep: str = SEP,
) -> list[str]:
    """
    Calcula cómo quedará Juegos_Este_Ano de cada jugador tras este evento.

    Cuenta:
      +1 por cada mesa jugada como jugador.
      +0 por arbitrar como GM (GMing no suma a Juegos_Este_Ano; el rol de
           árbitro ya se refleja en el sistema de pesos del algoritmo con 0.5).
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
        proyectado: int = actual + jugadas  # GMing no suma a Juegos_Este_Ano
        filas.append((proyectado, jugador.nombre, actual, jugadas, como_gm, proyectado))

    filas.sort(key=lambda r: (-r[0], r[1]))

    ancho: int = max(len(r[1]) for r in filas)
    enc: str = f"  {'Jugador':{ancho}}  Actual  +Juega  +GM  Proyectado"
    lineas: list[str] = [
        enc,
        "  " + "-" * (len(enc) - 2),
    ]
    for _, nombre, actual, jugadas, como_gm, proyectado in filas:
        lineas.append(
            f"  {nombre:{ancho}}    {actual:>3}     {jugadas:>3}   {como_gm:>2}         {proyectado:>3}"
        )

    return lineas


def _escribir_reporte(
    lineas_copypaste: list[str],
    lineas_detalle: list[str],
    lineas_proyeccion: list[str],
    lineas_registro: list[str],
    directorio: Path,
) -> Path:
    """Escribe el reporte en cuatro secciones y devuelve su ruta."""
    SEP_S: str = "═" * 44
    timestamp: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta: Path = directorio / f"reporte_{timestamp}.txt"

    def _seccion(titulo: str, lineas: list[str]) -> list[str]:
        return ["", SEP_S, f"  {titulo}", SEP_S] + lineas

    contenido: list[str] = (
        _seccion("LISTO PARA COMPARTIR", lineas_copypaste)
        + _seccion("DETALLE DEL EVENTO", lineas_detalle)
        + _seccion("PROYECCIÓN JUEGOS_ESTE_AÑO", lineas_proyeccion)
        + _seccion("REGISTRO", lineas_registro)
    )
    ruta.write_text("\n".join(contenido) + "\n", encoding="utf-8")
    return ruta


def _actualizar_csv(
    resultado: ResultadoPartidas,
    jugadores: list[Jugador],
    directorio: Path,
) -> Path:
    """
    Escribe el siguiente jugadores_NNNN.csv con los valores actualizados
    tras el evento. El archivo anterior queda intacto (inmutable).
    Devuelve la ruta del nuevo archivo.

    Cambios aplicados por jugador:
      - Juegos_Este_Ano  += mesas jugadas como jugador (GMing no suma)
      - Prioridad         = True si quedó en lista de espera, False si no
      - Experiencia       = "Antiguo" si era Nuevo y jugó al menos 1 mesa
      - Partidas_GM       = 0  (se reasigna manualmente en cada evento)
      - Partidas_Deseadas = sin cambios
    """
    cupos_jugados: Counter[str] = Counter(
        j.nombre for mesa in resultado.mesas for j in mesa.jugadores
    )
    nombres_en_espera: set[str] = {j.nombre for j in resultado.tickets_sobrantes}

    fieldnames: list[str] = [
        "Nombre", "Experiencia", "Juegos_Este_Ano",
        "Prioridad", "Partidas_Deseadas", "Partidas_GM",
    ]
    filas: list[dict] = []
    for jugador in jugadores:
        jugadas: int = cupos_jugados[jugador.nombre]
        fue_promovido: bool = jugador.es_nuevo and jugadas > 0
        filas.append({
            "Nombre":            jugador.nombre,
            "Experiencia":       "Antiguo" if (not jugador.es_nuevo or fue_promovido) else "Nuevo",
            "Juegos_Este_Ano":   jugador.juegos_ano + jugadas,
            "Prioridad":         str(jugador.nombre in nombres_en_espera),
            "Partidas_Deseadas": jugador.partidas_deseadas,
            "Partidas_GM":       0,
        })

    ruta_nueva: Path = siguiente_csv(directorio)
    with ruta_nueva.open(mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filas)

    return ruta_nueva


def organizar_partidas(directorio: str | Path = DIRECTORIO) -> None:
    directorio = Path(directorio)

    # ── Auto-detectar el CSV más reciente ────────────────────────────────────
    csv_path: Path | None = ultimo_csv(directorio)
    if csv_path is None:
        print("⚠️  No se encontró ningún jugadores_NNNN.csv en el directorio.")
        print("   Ejecuta primero: uv run python notion_sync.py")
        input("\nPresiona Enter para cerrar...")
        return

    jugadores: list[Jugador] = []

    # ── Leer CSV ──────────────────────────────────────────────────────────────
    with csv_path.open(mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            partidas_gm: int = int(row.get("Partidas_GM", 0) or 0)
            jugadores.append(Jugador(
                row["Nombre"], row["Experiencia"], row["Juegos_Este_Ano"],
                row["Prioridad"], row["Partidas_Deseadas"], partidas_gm,
            ))

    # ── Validar nombres únicos ─────────────────────────────────────────
    duplicados: list[str] = [
        n for n, c in Counter(j.nombre for j in jugadores).items() if c > 1
    ]
    if duplicados:
        print(f"⚠️  Nombres duplicados en el CSV: {', '.join(duplicados)}")
        input("\nPresiona Enter para salir...")
        return

    try:
        resultado: ResultadoPartidas | None = _calcular_partidas(jugadores)
    except ValueError as e:
        print(f"⚠️  Error de configuración: {e}")
        input("\nPresiona Enter para salir...")
        return

    if resultado is None:
        print("No hay suficientes jugadores para armar ni siquiera una partida de 7.")
        input("\nPresiona Enter para salir...")
        return

    sep: str = SEP

    # ── Calcular cambios del evento ───────────────────────────────────────────
    cupos_post: Counter[str] = Counter(
        j.nombre for mesa in resultado.mesas for j in mesa.jugadores
    )
    promovidos: list[str] = [
        j.nombre for j in jugadores if j.es_nuevo and cupos_post[j.nombre] > 0
    ]
    vistos: set[str] = set()
    con_prioridad: list[str] = []
    for j in resultado.tickets_sobrantes:
        if j.nombre not in vistos:
            vistos.add(j.nombre)
            con_prioridad.append(j.nombre)

    # ── Escribir siguiente CSV ────────────────────────────────────────────────
    ruta_nueva: Path = _actualizar_csv(resultado, jugadores, directorio)

    # ── Construir secciones del reporte ───────────────────────────────────────
    total_cupos: int = len(resultado.mesas) * 7
    total_tickets: int = total_cupos + resultado.minimo_teorico
    jugadores_en_espera: int = len({j.nombre for j in resultado.tickets_sobrantes})

    lineas_registro: list[str] = [
        f"  Generado:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Partidas:      {len(resultado.mesas)}  ({total_tickets} solicitados, {total_cupos} disponibles)",
        f"  En espera:     {jugadores_en_espera} jugador(es)",
        f"  Intentos:      {resultado.intentos_usados} de 200",
        f"  Leído de:      {csv_path.name}",
        f"  Escrito en:    {ruta_nueva.name}",
    ]
    if promovidos:
        lineas_registro.append(f"  Promovidos:    {', '.join(promovidos)}")
    if con_prioridad:
        lineas_registro.append(f"  Con prioridad: {', '.join(con_prioridad)}")

    ruta_reporte: Path = _escribir_reporte(
        lineas_copypaste=_formatear_copypaste(resultado),
        lineas_detalle=_formatear_resultado(resultado, sep),
        lineas_proyeccion=_construir_proyeccion(resultado, jugadores, sep),
        lineas_registro=lineas_registro,
        directorio=directorio,
    )

    # ── Consola: resumen mínimo ───────────────────────────────────────────────
    print(
        f"\n✓  {len(resultado.mesas)} partidas  |  "
        f"{total_tickets} solicitados, {total_cupos} disponibles, "
        f"{jugadores_en_espera} en espera  |  {resultado.intentos_usados} intento(s)"
    )
    print(f"✓  {ruta_reporte.name}")
    print(f"✓  {csv_path.name}  →  {ruta_nueva.name}")
    if promovidos:
        print(f"   Promovidos:  {', '.join(promovidos)}")
    if con_prioridad:
        print(f"   Prioridad:   {', '.join(con_prioridad)}")

    input("\nPresiona Enter para cerrar...")


if __name__ == "__main__":
    organizar_partidas()