"""Tablas de Steriflow.

Separadas de las de Ferlo a proposito y sin ninguna clave ajena contra ellas:
`steriflow_cycle.autoclave_code` es el numero que imprime la maquina (6..9), no
un `autoclave.id`. Los dos sistemas conviven en el mismo fichero SQLite pero no
se tocan, asi que borrar o reimportar uno nunca afecta al otro.

No hay paso de migracion asociado. Las dos tablas son puramente aditivas y se
crean con IF NOT EXISTS en cada conexion, de modo que una base v3 existente las
gana sin mas: subir `meta.schema_version` daria a entender que el esquema de
Ferlo ha cambiado, y no ha cambiado.

Identidad de un ciclo: (autoclave_code, started_at). El sha256 del fichero NO
sirve como clave -la maquina puede reimprimir el mismo ciclo y producir un PDF
distinto byte a byte-, pero se guarda para saber si el fichero cambio.
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
-- nombre no lleva el instante de arranque (ver `service._ya_importado`).
CREATE INDEX IF NOT EXISTS ix_sf_cycle_sha ON steriflow_cycle(autoclave_code, source_sha256);

-- Se guardan las SEIS fases aunque la interfaz solo muestre la 3. Son seis
-- filas por ciclo, no seis mil: mostrar manana otra fase pasa a ser un cambio
-- de interfaz en vez de reimportar meses de PDF.
CREATE TABLE IF NOT EXISTS steriflow_phase (
    cycle_id          INTEGER NOT NULL
                      REFERENCES steriflow_cycle(id) ON DELETE CASCADE,
    phase_number      INTEGER NOT NULL,
    phase_type        TEXT    NOT NULL DEFAULT '',
    start_ts          TEXT    NOT NULL,
    end_ts            TEXT    NOT NULL,
    duration_s        INTEGER NOT NULL,
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
