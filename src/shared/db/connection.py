"""Conexión a la base de datos compartida de TIFA.

Un único fichero SQLite para todos los módulos, en vez de uno por módulo: una
sola conexión que gestionar, un solo fichero que respaldar.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.shared.db.schema import ensure_schema
from src.shared.paths import DATA_DIR

DB_PATH = DATA_DIR / "tifa.db"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Abre la base de datos, creando el fichero y las tablas si hace falta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # WAL y no el journal por defecto: desde que el servidor web (otro proceso,
    # ver web/) escribe en este mismo fichero, con rollback journal un lector y
    # un escritor se excluyen y el que pierde se lleva un "database is locked".
    # En WAL los lectores no bloquean al escritor ni al revés; solo queda
    # escritor contra escritor, que es lo que absorbe busy_timeout. Es
    # propiedad del FICHERO, no de la conexión -se fija una vez y queda-, pero
    # se pide en cada connect() para que no dependa de qué proceso lo abrió
    # primero.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)
    return conn
