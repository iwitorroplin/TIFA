"""`ferlo_import`: qué ha llegado, no qué ficheros hay en disco.

Una fila por llegada -(machine, sha256)-, no por fichero mensual: ese fichero
crece cada día, así que su hash cambiaría a diario y no serviría como
identidad de nada. Lo que sí es estable es lo que entró por el buzón: unos
bytes concretos, con su ventana `from_ts..to_ts`. La unión de esas ventanas,
por máquina, es la única respuesta a "qué se ha visto ya" -ver
`logic/ingest/service.py:_cubierta`-.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
from pathlib import Path

from src.shared.db.iso import from_iso, to_iso


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def already_arrived(conn: sqlite3.Connection, machine: str, sha256: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM ferlo_import WHERE machine = ? AND sha256 = ?",
        (machine, sha256),
    ).fetchone() is not None


def covered_ranges(conn: sqlite3.Connection, machine: str) -> list[tuple[dt.datetime, dt.datetime]]:
    filas = conn.execute(
        "SELECT from_ts, to_ts FROM ferlo_import WHERE machine = ? ORDER BY from_ts",
        (machine,),
    ).fetchall()
    return [(from_iso(f["from_ts"]), from_iso(f["to_ts"])) for f in filas]


def record_arrival(
    conn: sqlite3.Connection,
    *,
    machine: str,
    arrived_as: str,
    sha256: str,
    from_ts: dt.datetime,
    to_ts: dt.datetime,
    rows: int,
    archived_to: list[Path],
) -> int:
    cur = conn.execute(
        "INSERT INTO ferlo_import"
        " (machine, arrived_as, sha256, from_ts, to_ts, rows, archived_to, imported_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            machine, arrived_as, sha256, to_iso(from_ts), to_iso(to_ts), rows,
            ",".join(str(p) for p in archived_to), to_iso(dt.datetime.now()),
        ),
    )
    return cur.lastrowid
