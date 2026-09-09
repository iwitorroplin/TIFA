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

from src.shared.db.iso import to_iso

from .models import CycleResult, Series, SterilizationProgram


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
        "SELECT code, target_temperature_c, target_time_min, is_active"
        " FROM ferlo_program WHERE code = ?",
        (code,),
    ).fetchone()
    if fila is None:
        return None
    return SterilizationProgram(
        code=fila["code"],
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
