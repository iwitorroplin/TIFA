"""Tablas de Steriflow en la base de datos compartida.

Sin ninguna clave ajena contra las de Ferlo, Macona o Pasteurización:
`steriflow_cycle.autoclave_code` es el número que imprime la máquina (6..9),
no un id de otra tabla. Los cuatro módulos conviven en el mismo fichero
SQLite pero no se tocan entre sí.

Identidad de un ciclo: (autoclave_code, started_at). El sha256 del fichero NO
sirve como clave -la máquina puede reimprimir el mismo ciclo y producir un PDF
distinto byte a byte-, pero se guarda para saber si el fichero cambió.
"""

from __future__ import annotations

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS steriflow_cycle (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    autoclave_code  INTEGER NOT NULL,
    started_at      TEXT    NOT NULL,
    cycle_number    TEXT    NOT NULL DEFAULT '',
    product         TEXT    NOT NULL DEFAULT '',
    batch           TEXT    NOT NULL DEFAULT '',
    cycles_counter  INTEGER,
    reported_at     TEXT,
    source_filename TEXT    NOT NULL,
    source_sha256   TEXT    NOT NULL,
    imported_at     TEXT    NOT NULL,

    UNIQUE (autoclave_code, started_at)
);
CREATE INDEX IF NOT EXISTS ix_sf_cycle_inicio ON steriflow_cycle(started_at);
-- Camino de respaldo de la ingesta: identificar por contenido un informe cuyo
-- nombre no lleva el instante de arranque.
CREATE INDEX IF NOT EXISTS ix_sf_cycle_sha ON steriflow_cycle(autoclave_code, source_sha256);

-- Se guardan las SEIS fases aunque la interfaz solo muestre la de
-- esterilización: son seis filas por ciclo, no seis mil.
CREATE TABLE IF NOT EXISTS steriflow_phase (
    cycle_id           INTEGER NOT NULL
                       REFERENCES steriflow_cycle(id) ON DELETE CASCADE,
    phase_number       INTEGER NOT NULL,
    phase_type         TEXT    NOT NULL DEFAULT '',
    start_ts           TEXT    NOT NULL,
    end_ts             TEXT    NOT NULL,
    duration_s         INTEGER NOT NULL,
    temperature_end_c  REAL,
    temperature_mean_c REAL,
    temperature_min_c  REAL,
    temperature_max_c  REAL,

    PRIMARY KEY (cycle_id, phase_number)
) WITHOUT ROWID;
"""


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Crea las tablas de Steriflow si faltan. Idempotente."""
    conn.executescript(DDL)
