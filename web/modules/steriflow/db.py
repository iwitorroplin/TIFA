"""Tabla `steriflow_web`: esquema, modelo y acceso a datos, todo junto -igual
que `src/modules/steriflow/logic/` agrupa lo suyo. El commit es cosa del
llamante (`web/modules/steriflow/routes.py`), no de este módulo -misma
convención que `src/modules/steriflow/logic/sterilization/repo.py`, donde el
repo hace SQL y el servicio hace `conn.commit()`.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from src.shared.db.iso import from_iso, to_iso

DDL = """
CREATE TABLE IF NOT EXISTS steriflow_web (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    temp_c      REAL    NOT NULL,
    created_by  TEXT    NOT NULL DEFAULT '',
    note        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sf_web_creado ON steriflow_web(created_at);
"""


def ensure_table(conn: sqlite3.Connection) -> None:
    """Crea `steriflow_web` si falta. Idempotente."""
    conn.executescript(DDL)


@dataclass(slots=True)
class SteriflowReading:
    """Una lectura mandada desde el navegador.

    Tabla aparte de `steriflow_cycle` (los PDF de la máquina, en
    `src/modules/steriflow/`): esto lo teclea una persona y no tiene ciclo al
    que colgarse, ni falta que hace -mezclarlas obligaría a dejar en NULL
    media tabla en cada inserción de una u otra.

    `created_by` es texto libre que teclea la propia persona -no hay login-,
    así que es una firma declarada, no una identidad verificada.
    """

    temp_c: float
    id: int | None = None
    created_by: str = ""
    note: str = ""
    created_at: dt.datetime | None = None


def save_reading(conn: sqlite3.Connection, reading: SteriflowReading) -> int:
    """Inserta la lectura y devuelve su id. No hace commit."""
    cursor = conn.execute(
        "INSERT INTO steriflow_web (temp_c, created_by, note, created_at) VALUES (?, ?, ?, ?)",
        (reading.temp_c, reading.created_by, reading.note, to_iso(reading.created_at)),
    )
    return cursor.lastrowid


def list_readings(conn: sqlite3.Connection, *, limit: int = 20) -> list[SteriflowReading]:
    """Las últimas `limit` lecturas, de la más reciente a la más antigua.

    Desempate por `id DESC` además de `created_at DESC`: dos lecturas del
    mismo segundo comparten el mismo ISO y solo el id las distingue.
    """
    filas = conn.execute(
        "SELECT * FROM steriflow_web ORDER BY created_at DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_row_to_reading(fila) for fila in filas]


def _row_to_reading(fila: sqlite3.Row) -> SteriflowReading:
    return SteriflowReading(
        id=fila["id"],
        temp_c=fila["temp_c"],
        created_by=fila["created_by"],
        note=fila["note"],
        created_at=from_iso(fila["created_at"]),
    )
