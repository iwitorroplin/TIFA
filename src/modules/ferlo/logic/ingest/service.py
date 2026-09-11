"""Orquesta la ruta diaria: entrada -> archivo -> análisis -> `tifa.db`.

    para cada CSV en entrada/<machine>/:
        ¿estos bytes exactos ya llegaron?           -> vacía entrada, sigue
        lee + agrupa por mes; separa lo nuevo de lo ya cubierto (D2)
        funde lo nuevo en el mensual de cada mes tocado (D1)
        registra la llegada en ferlo_import
    vacía la entrada entera (buzón transitorio): también lo que no era CSV
    importable, para que la carpeta quede como se la encontró el operario
    para cada mes tocado:
        relee el mensual entero (no solo lo nuevo: un ciclo puede empezar en
        datos ya archivados y seguir en los que acaban de llegar)
        segmenta y evalúa cada ciclo con el programa que ya tuviera asignado
        (nunca uno nuevo: ver logic/analysis/repo.py:existing_program_code)
        guarda

No dispara nada por su cuenta -ni vigilancia de carpeta ni planificador-: lo
llama un botón (D4) o el script de terminal (`logic/ingest/cli.py`).
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from src.modules.ferlo.logic.analysis import repo as analysis_repo
from src.modules.ferlo.logic.analysis.models import CycleResult, SterilizationProgram
from src.modules.ferlo.logic.analysis.programs import ManualSetpoint, manual_program
from src.modules.ferlo.logic.analysis.segment import segment
from src.modules.ferlo.logic.analysis.service import assign
from src.modules.ferlo.logic.config import Settings
from src.modules.ferlo.logic.logs import agent_logger
from src.shared.messages.types import MessageType

from . import archive, repo
from .checks import check_rows
from .normalize import build_series, parse_timestamp
from .reader import ReadReport, read_raw_rows


@dataclass(slots=True)
class ArrivalResult:
    filename: str
    rows: int
    new_rows: int
    already_seen: bool


@dataclass(slots=True)
class ImportSummary:
    machine: str
    arrivals: list[ArrivalResult] = field(default_factory=list)
    cycles_by_month: dict[tuple[int, int], list[CycleResult]] = field(default_factory=dict)
    # Ficheros que quedaban en la carpeta de entrada y no eran CSV importables
    # (ver `_vaciar_entrada`). Se cuentan aparte de `arrivals`: no aportaron
    # ninguna fila, pero conviene que se vea que estaban ahí y ya no están.
    leftovers_removed: int = 0

    @property
    def total_new_rows(self) -> int:
        return sum(a.new_rows for a in self.arrivals)

    @property
    def total_cycles(self) -> int:
        return sum(len(c) for c in self.cycles_by_month.values())


def _cubierta(ts: dt.datetime, rangos: list[tuple[dt.datetime, dt.datetime]]) -> bool:
    return any(desde <= ts <= hasta for desde, hasta in rangos)


def import_machine(
    conn: sqlite3.Connection, settings: Settings, machine: str
) -> ImportSummary:
    """Importa y analiza todo lo pendiente de `machine`. Es lo único que
    llama la UI (Fase 4) y el script de terminal."""
    log = agent_logger().scoped(machine)
    resumen = ImportSummary(machine=machine)
    entrada_dir = settings.entrada_dir / machine
    archivo_dir = settings.archivo_dir

    meses_tocados: set[tuple[int, int]] = set()

    for csv_path in sorted(entrada_dir.glob("*.csv")) if entrada_dir.exists() else []:
        sha = repo.sha256_of(csv_path)
        if repo.already_arrived(conn, machine, sha):
            log.log(f"{csv_path.name} ya habia llegado (mismos bytes), se omite")
            resumen.arrivals.append(ArrivalResult(csv_path.name, 0, 0, already_seen=True))
            csv_path.unlink()
            continue

        report = ReadReport()
        rows = read_raw_rows(csv_path, report)
        if not report.is_default_format:
            log.log(f"{csv_path.name} - detectado formato distinto del habitual "
                    f"(delimitador {report.delimiter!r}, codificación {report.encoding})")
        if report.rejected:
            ejemplos = ", ".join(repr(v) for v in report.rejected_samples)
            log.log(f"{csv_path.name} - {report.rejected} fila(s) con fecha ilegible "
                    f"descartada(s) (ejemplos: {ejemplos})", level=MessageType.WARNING)

        if not rows:
            log.log(f"{csv_path.name} sin filas, se omite", level=MessageType.WARNING)
            csv_path.unlink()
            continue

        chequeo = check_rows(rows)
        if not chequeo.cuadra:
            log.log(f"{csv_path.name} - patrones sin clasificar en TEMP/PRES "
                    f"({chequeo.resumen_texto()})", level=MessageType.WARNING)

        filas_con_ts = [(row, parse_timestamp(row.date_raw, row.time_raw)) for row in rows]
        rangos = repo.covered_ranges(conn, machine)
        nuevas = [row for row, ts in filas_con_ts if not _cubierta(ts, rangos)]

        rutas_archivadas: list[Path] = []
        if nuevas:
            for (anio, mes), filas_mes in archive.group_by_month(nuevas).items():
                ruta = archive.append_rows(archivo_dir, machine, anio, mes, filas_mes)
                rutas_archivadas.append(ruta)
                meses_tocados.add((anio, mes))

        from_ts = min(ts for _, ts in filas_con_ts)
        to_ts = max(ts for _, ts in filas_con_ts)
        repo.record_arrival(
            conn, machine=machine, arrived_as=csv_path.name, sha256=sha,
            from_ts=from_ts, to_ts=to_ts, rows=len(rows), archived_to=rutas_archivadas,
        )
        csv_path.unlink()

        log.log(f"{csv_path.name} - {len(rows)} filas, "
                f"{len(nuevas)} nuevas ({chequeo.resumen_texto()})")
        resumen.arrivals.append(
            ArrivalResult(csv_path.name, len(rows), len(nuevas), already_seen=False)
        )

    resumen.leftovers_removed = _vaciar_entrada(entrada_dir, log)

    for anio, mes in sorted(meses_tocados):
        ciclos = _reanalizar_mes(conn, settings, machine, anio, mes)
        resumen.cycles_by_month[(anio, mes)] = ciclos
        log.log(f"{anio:04d}-{mes:02d} - {len(ciclos)} ciclos")

    conn.commit()
    return resumen


def _vaciar_entrada(entrada_dir: Path, log) -> int:
    """Deja la carpeta de entrada vacía y creada. Devuelve cuántos restos quitó.

    La entrada es un buzón transitorio (D1): después de importar tiene que
    quedar vacía, y hasta ahora solo se borraban los `.csv` que se llegaban a
    procesar. Lo que fallaba al leerse, o lo que no era `.csv`, se quedaba ahí
    para siempre -y en la siguiente importación seguía apareciendo como si
    estuviera pendiente-.

    Borra ficheros, nunca carpetas: una subcarpeta ahí dentro la ha puesto una
    persona a propósito y no es de este código decidir que sobra. Un fichero
    que no se deja borrar (abierto en Excel, sin permisos) se anota y se sigue:
    dejar la carpeta a medio vaciar no puede tumbar una importación que ya ha
    terminado bien.
    """
    if not entrada_dir.exists():
        entrada_dir.mkdir(parents=True, exist_ok=True)
        return 0

    quitados = 0
    for resto in sorted(entrada_dir.iterdir()):
        if not resto.is_file():
            continue
        try:
            resto.unlink()
        except OSError as ex:
            log.log(f"No se pudo vaciar {resto.name} de la entrada: {ex}",
                    level=MessageType.WARNING)
            continue
        quitados += 1
        log.log(f"Quitado de la entrada: {resto.name}", level=MessageType.WARNING)

    entrada_dir.mkdir(parents=True, exist_ok=True)
    return quitados


def _reanalizar_mes(
    conn: sqlite3.Connection, settings: Settings, machine: str, anio: int, mes: int,
) -> list[CycleResult]:
    """Relee el mensual completo y reanaliza: renormalizar sigue siendo
    releer (no hace falta guardar una capa cruda para poder recalcular)."""
    serie = _leer_mes(settings, machine, anio, mes)
    ciclos = segment(serie, settings)
    for ciclo in ciclos:
        code = analysis_repo.existing_program_code(conn, machine, ciclo.start_ts)
        programa = analysis_repo.load_program(conn, code) if code is not None else None
        assign(serie, ciclo, settings, programa)
        analysis_repo.save_cycle(conn, machine, serie, ciclo)
    return ciclos


def _leer_mes(settings: Settings, machine: str, anio: int, mes: int):
    ruta = archive.monthly_archive_path(settings.archivo_dir, machine, anio, mes)
    rows = read_raw_rows(ruta)
    return build_series(machine, ruta.name, rows)


def _resolve_program(
    conn: sqlite3.Connection,
    program_code: int | None,
    manual: ManualSetpoint | None,
) -> SterilizationProgram | None:
    """Traduce lo que pidió la pantalla al programa con el que evaluar.

    Con `manual`, la consigna la puso una persona y NO se relee de
    `ferlo_program`: se construye al vuelo (ver
    `logic/analysis/programs.py:manual_program`). Releer la fila 0 haría que
    teclear una consigna nueva cambiara la de todos los ciclos manuales ya
    guardados, porque compartirían fila.
    """
    if manual is not None:
        return manual_program(manual.target_temperature_c, manual.target_time_min)
    if program_code is None:
        return None
    return analysis_repo.load_program(conn, program_code)


def reassign_programs(
    conn: sqlite3.Connection,
    settings: Settings,
    cycles: list[tuple[str, dt.datetime]],
    program_code: int | None,
    manual: ManualSetpoint | None = None,
) -> int:
    """Asigna (o quita) el mismo programa a varios ciclos. Devuelve cuántos se
    pudieron reasignar.

    Con `manual` se asigna la consigna tecleada a mano (programa 0) en vez de
    un programa de la lista; `program_code` se ignora entonces.

    Agrupa por máquina y mes para leer cada mensual UNA vez: `reassign_program`
    relee el fichero entero en cada llamada, y asignar 50 ciclos del mismo mes
    desde la pestaña de Ciclos lo leería 50 veces. Por lo demás hace
    exactamente lo mismo -misma relectura, misma reevaluación, misma escritura
    explícita del programa-, así que un ciclo asignado en bloque queda idéntico
    a uno asignado desde su ventana de detalle.
    """
    por_mes: dict[tuple[str, int, int], list[dt.datetime]] = {}
    for machine, started_at in cycles:
        por_mes.setdefault((machine, started_at.year, started_at.month), []).append(started_at)

    programa = _resolve_program(conn, program_code, manual)
    reasignados = 0

    for (machine, anio, mes), instantes in sorted(por_mes.items()):
        ruta = archive.monthly_archive_path(settings.archivo_dir, machine, anio, mes)
        if not ruta.exists():
            continue

        serie = _leer_mes(settings, machine, anio, mes)
        detectados = {c.start_ts: c for c in segment(serie, settings)}
        for started_at in instantes:
            objetivo = detectados.get(started_at)
            if objetivo is None:
                continue
            assign(serie, objetivo, settings, programa)
            cycle_id = analysis_repo.save_cycle(conn, machine, serie, objetivo)
            analysis_repo.write_program_assignment(conn, cycle_id, objetivo)
            reasignados += 1

    conn.commit()
    return reasignados


def reassign_program(
    conn: sqlite3.Connection,
    settings: Settings,
    machine: str,
    started_at: dt.datetime,
    program_code: int | None,
    manual: ManualSetpoint | None = None,
) -> CycleResult | None:
    """Asigna (o quita, con `program_code=None`) el programa de un ciclo ya
    guardado, y lo reevalúa. Con `manual` se asigna la consigna tecleada a
    mano (programa 0) y `program_code` se ignora. Es el único punto de la
    Fase 4 que escribe
    `program_code` -asignar es siempre un acto explícito (invariante de la
    Fase 0): a diferencia de `_reanalizar_mes`, aquí el programa lo dice
    quien llama, nunca `existing_program_code`.

    Relee el mensual completo -exactamente lo que haría la siguiente
    reimportación- para que fases, métricas y veredicto salgan idénticos a
    los que saldrían si se reimportara ahora mismo: no hay atajo que
    reconstruya la serie solo a partir de lo ya guardado sin perder las
    incidencias de fuera del ciclo que `validate.py` hereda por ventana.

    Devuelve `None` si el mensual no existe o el ciclo ya no aparece al
    segmentar de nuevo -por ejemplo, si los umbrales de detección cambiaron
    entre medias-.
    """
    ruta = archive.monthly_archive_path(settings.archivo_dir, machine, started_at.year, started_at.month)
    if not ruta.exists():
        return None

    serie = _leer_mes(settings, machine, started_at.year, started_at.month)
    ciclos = segment(serie, settings)
    objetivo = next((c for c in ciclos if c.start_ts == started_at), None)
    if objetivo is None:
        return None

    programa = _resolve_program(conn, program_code, manual)
    assign(serie, objetivo, settings, programa)
    cycle_id = analysis_repo.save_cycle(conn, machine, serie, objetivo)
    # save_cycle() nunca toca program_code en su rama de UPDATE -por diseño,
    # para que una reimportación no pueda deshacer una asignación (ver su
    # docstring)-. Esta es la única llamada de la Fase 4 que sí debe
    # cambiarlo, porque aquí el programa lo dice explícitamente quien llama.
    analysis_repo.write_program_assignment(conn, cycle_id, objetivo)
    conn.commit()
    return objetivo
