"""Conexión a la base de datos compartida de TIFA.

Un único fichero SQLite para todos los módulos, en vez de uno por módulo: una
sola conexión que gestionar, un solo fichero que respaldar.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.db.schema import ensure_schema

# src/db/connection.py -> parents[2] es la raíz del repo.
APP_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = APP_ROOT / "data" / "tifa.db"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Abre la base de datos, creando el fichero y las tablas si hace falta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)
    return conn
