"""Tabla `web_user`: quién puede entrar y a qué módulo tiene acceso.

`module` guarda el `id` de un `WebModuleSpec` de `web/registry.py`
(`"steriflow"`, `"ferlo"`...) -no hay clave ajena real porque esa lista vive
en Python, no en una tabla; la validez del valor se comprueba al sembrar
usuarios (`seed.py`), no aquí-. `ALL_MODULES` es el único valor especial: un
usuario con ese `module` (el admin de `seed.py`) tiene acceso a todos, no a
un id de módulo concreto -lo comprueban `web/auth.py::require_module` y las
plantillas, no esta tabla-.

Mismo patrón que `web/modules/steriflow/db.py`: DDL, modelo y acceso a datos
juntos en un solo fichero, funciones sueltas que reciben `conn` como primer
parámetro, y el commit es cosa del llamante.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from src.shared.db.iso import from_iso, to_iso

# Valor de `module` que da acceso a todos los módulos, no a uno concreto.
ALL_MODULES = "*"

DDL = """
CREATE TABLE IF NOT EXISTS web_user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    password_salt TEXT    NOT NULL,
    module        TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);
"""


def ensure_table(conn: sqlite3.Connection) -> None:
    """Crea `web_user` si falta. Idempotente."""
    conn.executescript(DDL)


@dataclass(slots=True)
class WebUser:
    id: int | None
    name: str
    password_hash: str
    password_salt: str
    module: str
    created_at: dt.datetime | None = None


def get_by_name(conn: sqlite3.Connection, name: str) -> WebUser | None:
    fila = conn.execute("SELECT * FROM web_user WHERE name = ?", (name,)).fetchone()
    return _row_to_user(fila) if fila is not None else None


def get_by_id(conn: sqlite3.Connection, user_id: int) -> WebUser | None:
    fila = conn.execute("SELECT * FROM web_user WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(fila) if fila is not None else None


def create_user(conn: sqlite3.Connection, name: str, password_hash: str, password_salt: str, module: str) -> int:
    """Da de alta el usuario y devuelve su id. No hace commit."""
    cursor = conn.execute(
        "INSERT INTO web_user (name, password_hash, password_salt, module, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, password_hash, password_salt, module, to_iso(dt.datetime.now())),
    )
    return cursor.lastrowid


def _row_to_user(fila: sqlite3.Row) -> WebUser:
    return WebUser(
        id=fila["id"],
        name=fila["name"],
        password_hash=fila["password_hash"],
        password_salt=fila["password_salt"],
        module=fila["module"],
        created_at=from_iso(fila["created_at"]),
    )
