"""Orquesta la ruta diaria: entrada -> archivo -> análisis -> `tifa.db`.

    para cada CSV en entrada/<machine>/:
        ¿estos bytes exactos ya llegaron?           -> vacía entrada, sigue
        lee + agrupa por mes; separa lo nuevo de lo ya cubierto (D2)
        funde lo nuevo en el mensual de cada mes tocado (D1)
        registra la llegada en ferlo_import
        vacía entrada (buzón transitorio)
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
from src.modules.ferlo.logic.analysis.models import CycleResult
from src.modules.ferlo.logic.analysis.segment import segment
from src.modules.ferlo.logic.analysis.service import assign
from src.modules.ferlo.logic.config import Settings
from src.modules.ferlo.logic.logs import agent_logger

from . import archive, repo
from .checks import check_rows
from .normalize import build_series, parse_timestamp
from .reader import RawRow, read_raw_rows


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
    log = agent_logger()
    resumen = ImportSummary(machine=machine)
    entrada_dir = settings.entrada_dir / machine
    archivo_dir = settings.archivo_dir

    meses_tocados: set[tuple[int, int]] = set()

    for csv_path in sorted(entrada_dir.glob("*.csv")) if entrada_dir.exists() else []:
        sha = repo.sha256_of(csv_path)
        if repo.already_arrived(conn, machine, sha):
            log.log(f"Ferlo {machine}: {csv_path.name} ya habia llegado (mismos bytes), se omite")
            resumen.arrivals.append(ArrivalResult(csv_path.name, 0, 0, already_seen=True))
            csv_path.unlink()
            continue

        rows = read_raw_rows(csv_path)
        if not rows:
            log.log(f"Ferlo {machine}: {csv_path.name} sin filas, se omite")
            csv_path.unlink()
            continue

        chequeo = check_rows(rows)
        if not chequeo.cuadra:
            log.log(f"Ferlo {machine}: {csv_path.name} - patrones sin clasificar en TEMP/PRES "
                     f"({chequeo.resumen_texto()})")

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

        log.log(f"Ferlo {machine}: {csv_path.name} - {len(rows)} filas, "
                 f"{len(nuevas)} nuevas ({chequeo.resumen_texto()})")
        resumen.arrivals.append(
            ArrivalResult(csv_path.name, len(rows), len(nuevas), already_seen=False)
        )

    for anio, mes in sorted(meses_tocados):
        ciclos = _reanalizar_mes(conn, settings, machine, archivo_dir, anio, mes)
        resumen.cycles_by_month[(anio, mes)] = ciclos
        log.log(f"Ferlo {machine}: {anio:04d}-{mes:02d} - {len(ciclos)} ciclos")

    conn.commit()
    return resumen


def _reanalizar_mes(
    conn: sqlite3.Connection, settings: Settings, machine: str,
    archivo_dir: Path, anio: int, mes: int,
) -> list[CycleResult]:
    """Relee el mensual completo y reanaliza: renormalizar sigue siendo
    releer (no hace falta guardar una capa cruda para poder recalcular)."""
    ruta = archive.monthly_archive_path(archivo_dir, machine, anio, mes)
    rows = read_raw_rows(ruta)
    serie = build_series(machine, ruta.name, rows)

    ciclos = segment(serie, settings)
    for ciclo in ciclos:
        code = analysis_repo.existing_program_code(conn, machine, ciclo.start_ts)
        programa = analysis_repo.load_program(conn, code) if code is not None else None
        assign(serie, ciclo, settings, programa)
        analysis_repo.save_cycle(conn, machine, serie, ciclo)
    return ciclos
