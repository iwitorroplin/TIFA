"""Acceso a las tablas de Steriflow.

`SteriflowCycleRow` es la vista de lectura -el ciclo guardado con sus fases-,
equivalente a lo que `storage.rows.CycleRow` es para Ferlo, pero sin nada que
ver con ella: aqui no hay estado, ni veredicto, ni programa asignado.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass, field

from ..storage.schema import from_iso, to_iso
from .models import STERILIZATION_PHASE_NUMBER, SteriflowCycle, SteriflowPhase


@dataclass(slots=True)
class SteriflowCycleRow:
    """Vista de lectura de un ciclo Steriflow guardado, con sus fases."""

    id: int
    autoclave_code: int
    started_at: dt.datetime
    cycle_number: str
    product: str
    batch: str
    cycles_counter: int | None
    reported_at: dt.datetime | None
    source_filename: str
    source_sha256: str
    imported_at: dt.datetime | None
    phases: list[SteriflowPhase] = field(default_factory=list)

    @property
    def sterilization(self) -> SteriflowPhase | None:
        return next(
            (p for p in self.phases if p.number == STERILIZATION_PHASE_NUMBER), None
        )

    @property
    def end_ts(self) -> dt.datetime | None:
        return self.phases[-1].end_ts if self.phases else None


def save_cycle(conn: sqlite3.Connection, cycle: SteriflowCycle) -> tuple[int, bool]:
    """Guarda un ciclo y sus fases. Devuelve (id, era_nuevo).

    Reimportar el mismo ciclo lo actualiza en vez de duplicarlo (UNIQUE sobre
    autoclave_code + started_at). Las fases se reescriben enteras: son datos de
    la maquina, no hay nada editado por una persona que se pueda perder.
    """
    fila = conn.execute(
        "SELECT id FROM steriflow_cycle WHERE autoclave_code = ? AND started_at = ?",
        (cycle.autoclave_code, to_iso(cycle.started_at)),
    ).fetchone()
    era_nuevo = fila is None

    conn.execute(
        "INSERT INTO steriflow_cycle("
        " autoclave_code, started_at, cycle_number, product, batch, cycles_counter,"
        " reported_at, source_filename, source_sha256, imported_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(autoclave_code, started_at) DO UPDATE SET "
        " cycle_number=excluded.cycle_number, product=excluded.product,"
        " batch=excluded.batch, cycles_counter=excluded.cycles_counter,"
        " reported_at=excluded.reported_at, source_filename=excluded.source_filename,"
        " source_sha256=excluded.source_sha256, imported_at=excluded.imported_at",
        (
            cycle.autoclave_code, to_iso(cycle.started_at), cycle.cycle_number,
            cycle.product, cycle.batch, cycle.cycles_counter,
            to_iso(cycle.reported_at), cycle.source_filename, cycle.source_sha256,
            to_iso(dt.datetime.now()),
        ),
    )
    cycle_id = conn.execute(
        "SELECT id FROM steriflow_cycle WHERE autoclave_code = ? AND started_at = ?",
        (cycle.autoclave_code, to_iso(cycle.started_at)),
    ).fetchone()["id"]

    conn.execute("DELETE FROM steriflow_phase WHERE cycle_id = ?", (cycle_id,))
    conn.executemany(
        "INSERT INTO steriflow_phase("
        " cycle_id, phase_number, phase_type, start_ts, end_ts, duration_s,"
        " temperature_end_c, temperature_mean_c, temperature_min_c, temperature_max_c) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (cycle_id, f.number, f.type_name, to_iso(f.start_ts), to_iso(f.end_ts),
             f.duration_s, f.temperature_end_c, f.temperature_mean_c,
             f.temperature_min_c, f.temperature_max_c)
            for f in cycle.phases
        ],
    )
    return cycle_id, era_nuevo


def find_by_sha(
    conn: sqlite3.Connection, autoclave_code: int, sha256: str
) -> int | None:
    """id del ciclo ya importado desde un fichero identico, si lo hay.

    Es lo que permite reimportar una carpeta entera sin volver a abrir los PDF
    ya conocidos: leer uno cuesta ~1 s y una carpeta acumula meses de ciclos.
    """
    fila = conn.execute(
        "SELECT id FROM steriflow_cycle WHERE autoclave_code = ? AND source_sha256 = ?",
        (autoclave_code, sha256),
    ).fetchone()
    return fila["id"] if fila else None


def known_start_times(conn: sqlite3.Connection, autoclave_code: int) -> set[dt.datetime]:
    """Instantes de arranque ya guardados de un autoclave.

    Una consulta para toda la carpeta. Es lo que permite decidir si un informe
    ya esta importado sin abrirlo ni leerlo: el nombre del fichero lleva ese
    mismo instante (ver `reader.started_at_from_filename`).
    """
    filas = conn.execute(
        "SELECT started_at FROM steriflow_cycle WHERE autoclave_code = ?",
        (autoclave_code,),
    ).fetchall()
    return {from_iso(f["started_at"]) for f in filas}


def list_cycles(
    conn: sqlite3.Connection, *, autoclave_code: int | None = None
) -> list[SteriflowCycleRow]:
    """Todos los ciclos guardados, del mas reciente al mas antiguo."""
    sql = "SELECT * FROM steriflow_cycle"
    params: tuple = ()
    if autoclave_code is not None:
        sql += " WHERE autoclave_code = ?"
        params = (autoclave_code,)
    sql += " ORDER BY started_at DESC"

    filas = conn.execute(sql, params).fetchall()
    if not filas:
        return []

    fases = _phases_by_cycle(conn, [f["id"] for f in filas])
    return [
        SteriflowCycleRow(
            id=f["id"],
            autoclave_code=f["autoclave_code"],
            started_at=from_iso(f["started_at"]),
            cycle_number=f["cycle_number"],
            product=f["product"],
            batch=f["batch"],
            cycles_counter=f["cycles_counter"],
            reported_at=from_iso(f["reported_at"]),
            source_filename=f["source_filename"],
            source_sha256=f["source_sha256"],
            imported_at=from_iso(f["imported_at"]),
            phases=fases.get(f["id"], []),
        )
        for f in filas
    ]


def _phases_by_cycle(
    conn: sqlite3.Connection, cycle_ids: list[int]
) -> dict[int, list[SteriflowPhase]]:
    """Las fases de todos los ciclos en UNA consulta.

    Una consulta por ciclo dentro del bucle de `list_cycles` convierte un
    listado de 2.000 ciclos en 2.001 consultas.
    """
    marcas = ",".join("?" * len(cycle_ids))
    filas = conn.execute(
        f"SELECT * FROM steriflow_phase WHERE cycle_id IN ({marcas}) "
        f"ORDER BY cycle_id, phase_number",
        cycle_ids,
    ).fetchall()

    out: dict[int, list[SteriflowPhase]] = {}
    for f in filas:
        out.setdefault(f["cycle_id"], []).append(SteriflowPhase(
            number=f["phase_number"],
            type_name=f["phase_type"],
            start_ts=from_iso(f["start_ts"]),
            end_ts=from_iso(f["end_ts"]),
            duration_s=f["duration_s"],
            temperature_end_c=f["temperature_end_c"],
            temperature_mean_c=f["temperature_mean_c"],
            temperature_min_c=f["temperature_min_c"],
            temperature_max_c=f["temperature_max_c"],
        ))
    return out


def delete_cycles(conn: sqlite3.Connection, *, autoclave_code: int | None = None) -> int:
    """Borra el historico de Steriflow (todo, o de un autoclave). Devuelve cuantos."""
    if autoclave_code is None:
        n = conn.execute("SELECT COUNT(*) AS n FROM steriflow_cycle").fetchone()["n"]
        conn.execute("DELETE FROM steriflow_cycle")
    else:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM steriflow_cycle WHERE autoclave_code = ?",
            (autoclave_code,),
        ).fetchone()["n"]
        conn.execute(
            "DELETE FROM steriflow_cycle WHERE autoclave_code = ?", (autoclave_code,)
        )
    return n
