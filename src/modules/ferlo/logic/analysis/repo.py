"""Persiste un `CycleResult` (con sus muestras e incidencias) en `ferlo_cycle`
/ `ferlo_sample` / `ferlo_incident`.

Identidad: (machine, started_at) -ver logic/schema.py-. Reimportar el mismo
ciclo actualiza sus columnas calculadas en vez de duplicarlo, pero nunca toca
`program_code`, `target_temperature_c`, `target_time_min`, `manual_verdict` ni
`review_notes`: eso solo lo escribe quien asigna un programa o revisa un
ciclo a mano (todavia sin construir; Fase 4), nunca un reanalisis. Es el
invariante "importar nunca asigna programa" de la Fase 0, aplicado aqui.

`ferlo_sample`/`ferlo_incident` sí se recrean enteras en cada guardado: son
derivadas por completo del analisis, no hay ninguna decision de una persona
que perder.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass

from src.shared.db.iso import from_iso, to_iso

from .models import (
    CycleResult,
    CycleStatus,
    Finding,
    FindingCode,
    ManualVerdict,
    Series,
    Severity,
    SterilizationProgram,
)


def existing_program_code(
    conn: sqlite3.Connection, machine: str, started_at: dt.datetime
) -> int | None:
    """El programa que ya tenía asignado este ciclo, si lo tenía.

    Lo usa `logic/ingest/service.py` antes de reanalizar: sin esto, una
    reimportación (que llama a `assign()` sin saber qué eligió antes una
    persona) resetearía el ciclo a UNASSIGNED cada vez que se reimporta el
    mes -justo lo que el invariante "importar nunca asigna programa" prohíbe.
    """
    fila = conn.execute(
        "SELECT program_code FROM ferlo_cycle WHERE machine = ? AND started_at = ?",
        (machine, to_iso(started_at)),
    ).fetchone()
    return fila["program_code"] if fila is not None else None


def load_program(conn: sqlite3.Connection, code: int) -> SterilizationProgram | None:
    fila = conn.execute(
        "SELECT code, name, target_temperature_c, target_time_min, is_active"
        " FROM ferlo_program WHERE code = ?",
        (code,),
    ).fetchone()
    return program_from_row(fila) if fila is not None else None


def program_from_row(fila: sqlite3.Row) -> SterilizationProgram:
    return SterilizationProgram(
        code=fila["code"],
        name=fila["name"] or "",
        target_temperature_c=fila["target_temperature_c"],
        target_time_min=fila["target_time_min"],
        is_active=bool(fila["is_active"]),
    )


def save_cycle(conn: sqlite3.Connection, machine: str, serie: Series, cycle: CycleResult) -> int:
    """Guarda o actualiza el ciclo y sus muestras/incidencias. Devuelve el id."""
    existente = conn.execute(
        "SELECT id FROM ferlo_cycle WHERE machine = ? AND started_at = ?",
        (machine, to_iso(cycle.start_ts)),
    ).fetchone()

    calculados = (
        to_iso(cycle.end_ts), cycle.measured_setpoint_c, cycle.peak_temperature_c,
        cycle.evaluation_setpoint_c, cycle.mean_temperature_c,
        cycle.mean_stable_temperature_c, cycle.temperature_min_c, cycle.temperature_max_c,
        cycle.time_below_setpoint_min, cycle.time_deviation_min, cycle.extra_time_min,
        cycle.coverage_pct, cycle.max_blind_window_s, cycle.uncovered_min,
        cycle.status.value, json.dumps(cycle.criteria), to_iso(dt.datetime.now()),
    )

    if existente is not None:
        cycle_id = existente["id"]
        conn.execute(
            "UPDATE ferlo_cycle SET"
            " ended_at=?, measured_setpoint_c=?, peak_temperature_c=?,"
            " evaluation_setpoint_c=?, mean_temperature_c=?, mean_stable_temperature_c=?,"
            " temperature_min_c=?, temperature_max_c=?, time_below_setpoint_min=?,"
            " time_deviation_min=?, extra_time_min=?, coverage_pct=?, max_blind_window_s=?,"
            " uncovered_min=?, status=?, thresholds_json=?, imported_at=?"
            " WHERE id=?",
            (*calculados, cycle_id),
        )
    else:
        cur = conn.execute(
            "INSERT INTO ferlo_cycle("
            " machine, started_at, ended_at, measured_setpoint_c, peak_temperature_c,"
            " evaluation_setpoint_c, program_code, target_temperature_c, target_time_min,"
            " mean_temperature_c, mean_stable_temperature_c, temperature_min_c,"
            " temperature_max_c, time_below_setpoint_min, time_deviation_min, extra_time_min,"
            " coverage_pct, max_blind_window_s, uncovered_min, status, manual_verdict,"
            " thresholds_json, imported_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'none', ?, ?)",
            (
                machine, to_iso(cycle.start_ts), to_iso(cycle.end_ts),
                cycle.measured_setpoint_c, cycle.peak_temperature_c,
                cycle.evaluation_setpoint_c, cycle.program_code,
                cycle.target_temperature_c, cycle.target_time_min,
                cycle.mean_temperature_c, cycle.mean_stable_temperature_c,
                cycle.temperature_min_c, cycle.temperature_max_c,
                cycle.time_below_setpoint_min, cycle.time_deviation_min, cycle.extra_time_min,
                cycle.coverage_pct, cycle.max_blind_window_s, cycle.uncovered_min,
                cycle.status.value, json.dumps(cycle.criteria), to_iso(dt.datetime.now()),
            ),
        )
        cycle_id = cur.lastrowid

    _replace_samples(conn, cycle_id, serie, cycle)
    _replace_incidents(conn, cycle_id, cycle)
    return cycle_id


def write_program_assignment(conn: sqlite3.Connection, cycle_id: int, cycle: CycleResult) -> None:
    """Escribe `program_code`/`target_temperature_c`/`target_time_min` de un
    ciclo ya guardado -las tres columnas que `save_cycle` protege a propósito
    en su rama de UPDATE (ver su docstring)-.

    Es la única función con permiso para tocarlas fuera del INSERT inicial, y
    solo la llama `logic/ingest/service.py:reassign_program`: el único punto
    de la Fase 4 donde asignar programa es un acto explícito de una persona,
    nunca el resultado de una reimportación.
    """
    conn.execute(
        "UPDATE ferlo_cycle SET program_code=?, target_temperature_c=?, target_time_min=?"
        " WHERE id=?",
        (cycle.program_code, cycle.target_temperature_c, cycle.target_time_min, cycle_id),
    )


def _replace_samples(
    conn: sqlite3.Connection, cycle_id: int, serie: Series, cycle: CycleResult
) -> None:
    conn.execute("DELETE FROM ferlo_sample WHERE cycle_id = ?", (cycle_id,))
    conn.executemany(
        "INSERT INTO ferlo_sample (cycle_id, ts, temperature_c) VALUES (?, ?, ?)",
        [
            (cycle_id, to_iso(serie.ts[i]), serie.temperature_c[i])
            for i in range(cycle.start_index, cycle.end_index + 1)
        ],
    )


def _replace_incidents(conn: sqlite3.Connection, cycle_id: int, cycle: CycleResult) -> None:
    conn.execute("DELETE FROM ferlo_incident WHERE cycle_id = ?", (cycle_id,))
    conn.executemany(
        "INSERT INTO ferlo_incident (cycle_id, code, severity, message, ts, value)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (cycle_id, f.code.value, f.severity.value, f.message, to_iso(f.ts), f.value)
            for f in cycle.findings
        ],
    )


# --- Consultas para la pestaña de ciclos y el detalle (Fase 4) ---
#
# `CycleRow` es una fila de `ferlo_cycle` ya lista para pintar: no es
# `CycleResult` -ese es el resultado en memoria de segmentar+evaluar, con
# indices sobre una `Series` que aqui ya no existe-. El nombre del programa
# llega por LEFT JOIN porque un ciclo puede estar sin asignar (D-notice de la
# Fase 4: "importar nunca asigna programa").


@dataclass(slots=True, frozen=True)
class CycleRow:
    id: int
    machine: str
    started_at: dt.datetime
    ended_at: dt.datetime
    measured_setpoint_c: float
    peak_temperature_c: float
    evaluation_setpoint_c: float
    program_code: int | None
    program_name: str
    target_temperature_c: float | None
    target_time_min: float | None
    mean_temperature_c: float | None
    mean_stable_temperature_c: float | None
    time_below_setpoint_min: float | None
    time_deviation_min: float | None
    coverage_pct: float | None
    status: CycleStatus
    manual_verdict: str
    review_notes: str | None
    imported_at: dt.datetime

    @property
    def duration_min(self) -> float:
        """Duracion total del ciclo (calentamiento + esterilizacion +
        enfriamiento). La duracion de solo la fase de esterilizacion no se
        guarda como columna aparte; se deriva de `target_time_min` +
        `time_deviation_min` cuando hay programa asignado."""
        return (self.ended_at - self.started_at).total_seconds() / 60.0

    @property
    def sterilization_duration_min(self) -> float | None:
        if self.target_time_min is None or self.time_deviation_min is None:
            return None
        return self.target_time_min + self.time_deviation_min

    @property
    def needs_review(self) -> bool:
        """Pendiente de que una persona lo mire: sin veredicto manual y no ya
        OK. Un ciclo UNASSIGNED tambien cuenta -sin programa no hay
        conformidad que declarar-."""
        return self.manual_verdict == "none" and self.status is not CycleStatus.OK


def _cycle_row(fila: sqlite3.Row) -> CycleRow:
    return CycleRow(
        id=fila["id"],
        machine=fila["machine"],
        started_at=from_iso(fila["started_at"]),
        ended_at=from_iso(fila["ended_at"]),
        measured_setpoint_c=fila["measured_setpoint_c"],
        peak_temperature_c=fila["peak_temperature_c"],
        evaluation_setpoint_c=fila["evaluation_setpoint_c"],
        program_code=fila["program_code"],
        program_name=fila["program_name"] or "",
        target_temperature_c=fila["target_temperature_c"],
        target_time_min=fila["target_time_min"],
        mean_temperature_c=fila["mean_temperature_c"],
        mean_stable_temperature_c=fila["mean_stable_temperature_c"],
        time_below_setpoint_min=fila["time_below_setpoint_min"],
        time_deviation_min=fila["time_deviation_min"],
        coverage_pct=fila["coverage_pct"],
        status=CycleStatus(fila["status"]),
        manual_verdict=fila["manual_verdict"],
        review_notes=fila["review_notes"],
        imported_at=from_iso(fila["imported_at"]),
    )


_CYCLE_SELECT = (
    "SELECT c.*, p.name AS program_name FROM ferlo_cycle c"
    " LEFT JOIN ferlo_program p ON p.code = c.program_code"
)


def _cycle_filters_sql(
    *,
    machine: str | None,
    date_from: dt.date | None,
    date_to: dt.date | None,
    needs_review: bool | None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if machine:
        clauses.append("c.machine = ?")
        params.append(machine)
    if date_from is not None:
        clauses.append("c.started_at >= ?")
        params.append(to_iso(dt.datetime.combine(date_from, dt.time.min)))
    if date_to is not None:
        clauses.append("c.started_at <= ?")
        params.append(to_iso(dt.datetime.combine(date_to, dt.time.max)))
    if needs_review:
        # Mismo criterio que CycleRow.needs_review, en SQL: sin veredicto
        # manual y no ya OK.
        clauses.append("c.manual_verdict = 'none' AND c.status != ?")
        params.append(CycleStatus.OK.value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def count_cycles(
    conn: sqlite3.Connection,
    *,
    machine: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    needs_review: bool | None = None,
) -> int:
    where, params = _cycle_filters_sql(
        machine=machine, date_from=date_from, date_to=date_to, needs_review=needs_review
    )
    fila = conn.execute(f"SELECT COUNT(*) AS n FROM ferlo_cycle c{where}", params).fetchone()
    return fila["n"]


def list_cycles(
    conn: sqlite3.Connection,
    *,
    machine: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    needs_review: bool | None = None,
    limit: int,
    offset: int = 0,
) -> list[CycleRow]:
    where, params = _cycle_filters_sql(
        machine=machine, date_from=date_from, date_to=date_to, needs_review=needs_review
    )
    filas = conn.execute(
        f"{_CYCLE_SELECT}{where} ORDER BY c.started_at DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return [_cycle_row(f) for f in filas]


def get_cycle(conn: sqlite3.Connection, cycle_id: int) -> CycleRow | None:
    fila = conn.execute(f"{_CYCLE_SELECT} WHERE c.id = ?", (cycle_id,)).fetchone()
    return _cycle_row(fila) if fila is not None else None


def list_samples(conn: sqlite3.Connection, cycle_id: int) -> list[tuple[dt.datetime, float | None]]:
    """Muestras del ciclo, en orden: lo que dibuja la curva del detalle."""
    filas = conn.execute(
        "SELECT ts, temperature_c FROM ferlo_sample WHERE cycle_id = ? ORDER BY ts",
        (cycle_id,),
    ).fetchall()
    return [(from_iso(f["ts"]), f["temperature_c"]) for f in filas]


def list_incidents(conn: sqlite3.Connection, cycle_id: int) -> list[Finding]:
    filas = conn.execute(
        "SELECT code, severity, message, ts, value FROM ferlo_incident"
        " WHERE cycle_id = ? ORDER BY ts",
        (cycle_id,),
    ).fetchall()
    return [
        Finding(
            code=FindingCode(f["code"]),
            severity=Severity(f["severity"]),
            message=f["message"],
            ts=from_iso(f["ts"]),
            value=f["value"],
        )
        for f in filas
    ]


def set_manual_verdict(
    conn: sqlite3.Connection, cycle_id: int, verdict: ManualVerdict, notes: str | None
) -> None:
    """Escribe el veredicto de una persona. Nunca lo toca una reimportacion
    -ver el docstring de este modulo y `logic/ingest/service.py`-."""
    conn.execute(
        "UPDATE ferlo_cycle SET manual_verdict = ?, review_notes = ? WHERE id = ?",
        (verdict.value, notes, cycle_id),
    )
    conn.commit()
