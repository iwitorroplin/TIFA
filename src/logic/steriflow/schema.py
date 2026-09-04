"""Tablas de Steriflow en la base de datos compartida.

Sin ninguna clave ajena contra las de Ferlo, Macona o Pasteurización:
`steriflow_cycle.autoclave_code` es el número que imprime la máquina (6..9),
no un id de otra tabla. Los cuatro módulos conviven en el mismo fichero
SQLite pero no se tocan entre sí.

Identidad de un ciclo: (autoclave_code, started_at). El sha256 del fichero NO
sirve como clave -la máquina puede reimprimir el mismo ciclo y producir un PDF
distinto byte a byte-, pero se guarda para saber si el fichero cambió.

De las seis fases que trae cada informe solo importa la 3 (esterilización), así
que sus datos van aplanados directamente en `steriflow_cycle` en vez de en una
tabla de fases aparte: no hay nada que normalizar para una sola fase por ciclo.
Si esa fase no se puede leer bien -o no se puede leer en absoluto- el ciclo se
guarda igual, con lo que sí se pudo extraer y `needs_review` a 1: el operario lo
revisa a mano en vez de que el dato desaparezca en silencio.
"""

from __future__ import annotations

import sqlite3

DDL = """
-- Qué PDF ya ha completado el backup a servidor, para no volver a
-- comprobarlos ni reprocesarlos en cada ejecución. Se escribe en cuanto el
-- robocopy hacia el servidor confirma la copia, antes de leer nada dentro del
-- PDF. `extracted_at` se fija al primer intento de lectura, tenga éxito o no
-- -si un PDF concreto no da ningún ciclo, no tiene sentido reabrirlo en cada
-- backup con la misma lógica que ya falló-.
--
-- `autoclave` es el nombre configurado (AutoclaveConfig.name, p.ej.
-- "AUTOCLAVE6"): es lo único que se conoce en este punto, antes de abrir el
-- PDF. El código numérico que imprime la máquina dentro del informe solo se
-- sabe tras leerlo, y es el que identifica `steriflow_cycle` -los dos no
-- tienen por qué coincidir como texto, así que no se comparan entre sí-.
CREATE TABLE IF NOT EXISTS steriflow_backup_file (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    autoclave         TEXT    NOT NULL,
    filename          TEXT    NOT NULL,
    sha256            TEXT    NOT NULL,
    backed_up_at      TEXT    NOT NULL,
    extracted_at      TEXT,
    extraction_error  TEXT,

    UNIQUE (autoclave, filename)
);
CREATE INDEX IF NOT EXISTS ix_sf_backup_file_pendientes
    ON steriflow_backup_file(autoclave, extracted_at);

CREATE TABLE IF NOT EXISTS steriflow_cycle (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    autoclave_code            INTEGER NOT NULL,
    started_at                TEXT    NOT NULL,
    cycle_number              TEXT    NOT NULL DEFAULT '',
    product                   TEXT    NOT NULL DEFAULT '',
    batch                     TEXT    NOT NULL DEFAULT '',
    cycles_counter            INTEGER,
    reported_at               TEXT,
    source_filename           TEXT    NOT NULL,
    source_sha256             TEXT    NOT NULL,

    -- Fase 3 del informe (esterilización). Puede quedar entera a NULL si la
    -- fila no se pudo leer: el resto de la cabecera ya identifica el ciclo.
    sterilization_start_ts    TEXT,
    sterilization_end_ts      TEXT,
    sterilization_duration_s  INTEGER,
    sterilization_temp_end_c  REAL,
    sterilization_temp_mean_c REAL,
    sterilization_temp_min_c  REAL,
    sterilization_temp_max_c  REAL,

    needs_review              INTEGER NOT NULL DEFAULT 0,
    review_notes              TEXT,
    imported_at               TEXT    NOT NULL,

    UNIQUE (autoclave_code, started_at)
);
CREATE INDEX IF NOT EXISTS ix_sf_cycle_inicio ON steriflow_cycle(started_at);
-- Camino de respaldo de la ingesta: identificar por contenido un informe cuyo
-- nombre no lleva el instante de arranque.
CREATE INDEX IF NOT EXISTS ix_sf_cycle_sha ON steriflow_cycle(autoclave_code, source_sha256);
"""


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Crea las tablas de Steriflow si faltan. Idempotente."""
    conn.executescript(DDL)
