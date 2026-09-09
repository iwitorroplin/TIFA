"""Tablas de Ferlo en la base de datos compartida `tifa.db`.

Fase 3 del port. Sin ninguna clave ajena contra las de Steriflow, Macona o
Pasteurización -los cuatro módulos conviven en el mismo fichero SQLite pero no
se tocan entre sí-.

`ferlo_sample` cuelga del ciclo (D3): no hay tabla de muestras suelta ni capa
cruda en la base -la máquina está fría dos de cada tres muestras, y esas no se
guardan nunca-. La capa cruda de verdad es el CSV archivado (Fase 1, D1), no
una tabla: `ferlo_import` es solo el registro de qué ha llegado -una fila por
llegada (machine, sha256), no por fichero en disco, porque el mensual del
archivo crece cada día y su hash cambiaría a diario si fuera la identidad-.

Identidad de un ciclo: (machine, started_at). `manual_verdict` vive en su
propia columna, aparte de `status` (el veredicto calculado): reanalizar un
ciclo no puede deshacer en silencio lo que decidió una persona -ver
`logic/analysis/repo.py:save_cycle`-.
"""

from __future__ import annotations

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS ferlo_import (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    machine      TEXT    NOT NULL,
    -- Nombre con el que llego a la carpeta de entrada. Una etiqueta, no una
    -- identidad -el README del origen ya avisaba de que no esta garantizado-.
    arrived_as   TEXT    NOT NULL,
    sha256       TEXT    NOT NULL,
    from_ts      TEXT    NOT NULL,
    to_ts        TEXT    NOT NULL,
    rows         INTEGER NOT NULL,
    -- Mensual(es) del archivo a los que se fundio (D1). Vacio si esta
    -- llegada no traia ninguna fila nueva -todo lo que traia ya estaba
    -- cubierto por una llegada anterior-.
    archived_to  TEXT    NOT NULL DEFAULT '',
    imported_at  TEXT    NOT NULL,

    UNIQUE (machine, sha256)
);
CREATE INDEX IF NOT EXISTS ix_ferlo_import_machine ON ferlo_import(machine, from_ts);

CREATE TABLE IF NOT EXISTS ferlo_program (
    code               INTEGER PRIMARY KEY,
    name               TEXT    NOT NULL DEFAULT '',
    target_temperature_c REAL NOT NULL,
    target_time_min    REAL    NOT NULL,
    is_active          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ferlo_cycle (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    machine                   TEXT    NOT NULL,
    started_at                TEXT    NOT NULL,
    ended_at                  TEXT    NOT NULL,

    -- etapa 3a: segmentacion, sin saber el programa
    measured_setpoint_c       REAL    NOT NULL,
    peak_temperature_c        REAL    NOT NULL,
    evaluation_setpoint_c     REAL    NOT NULL,

    -- etapa 3b/3c: requieren programa asignado. Asignar es siempre un acto
    -- explicito (ver invariantes de la Fase 0): reimportar nunca lo toca.
    program_code              INTEGER REFERENCES ferlo_program(code),
    target_temperature_c      REAL,
    target_time_min           REAL,

    mean_temperature_c        REAL,
    mean_stable_temperature_c REAL,
    temperature_min_c         REAL,
    temperature_max_c         REAL,
    time_below_setpoint_min   REAL,
    time_deviation_min        REAL,
    extra_time_min            REAL,

    -- cobertura de datos de la fase de esterilizacion: se calcula y se
    -- muestra, pero no decide el veredicto (D6).
    coverage_pct              REAL,
    max_blind_window_s        REAL,
    uncovered_min             REAL,

    status                    TEXT    NOT NULL,
    -- Veredicto de una persona, si lo hay. 'none' = todavia no revisado.
    -- Nunca lo escribe una reimportacion, solo la pantalla de revision.
    manual_verdict             TEXT    NOT NULL DEFAULT 'none',
    review_notes               TEXT,

    -- Umbrales con los que se juzgo este ciclo, congelados en JSON: subir
    -- manana una tolerancia no puede cambiar en silencio un veredicto ya
    -- dado.
    thresholds_json            TEXT    NOT NULL DEFAULT '{}',

    imported_at                TEXT    NOT NULL,

    UNIQUE (machine, started_at)
);
CREATE INDEX IF NOT EXISTS ix_ferlo_cycle_started_at ON ferlo_cycle(started_at);
CREATE INDEX IF NOT EXISTS ix_ferlo_cycle_status ON ferlo_cycle(status);

CREATE TABLE IF NOT EXISTS ferlo_sample (
    cycle_id      INTEGER NOT NULL REFERENCES ferlo_cycle(id) ON DELETE CASCADE,
    ts            TEXT    NOT NULL,
    temperature_c REAL,

    UNIQUE (cycle_id, ts)
);

CREATE TABLE IF NOT EXISTS ferlo_incident (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id  INTEGER NOT NULL REFERENCES ferlo_cycle(id) ON DELETE CASCADE,
    code      TEXT    NOT NULL,
    severity  TEXT    NOT NULL,
    message   TEXT    NOT NULL,
    ts        TEXT,
    value     REAL
);
CREATE INDEX IF NOT EXISTS ix_ferlo_incident_cycle ON ferlo_incident(cycle_id);
"""


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Crea las tablas de Ferlo si faltan. Idempotente (D8)."""
    conn.executescript(DDL)
