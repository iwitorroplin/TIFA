"""Columnas que se añaden a una tabla que ya existe.

El `CREATE TABLE IF NOT EXISTS` de cada módulo (`logic/schema.py`) crea la
tabla completa en una instalación nueva, pero no toca la que ya está: una
instalación en marcha se quedaría sin las columnas nuevas y fallaría al leer.
Aquí está la única forma de arreglarlo que no depende de recordar en qué
versión se añadió cada cosa: mirar qué columnas tiene la tabla ahora mismo y
añadir las que falten.

Solo sirve para AÑADIR. Cambiar el tipo de una columna, quitarla o tocar un
UNIQUE obliga en SQLite a reconstruir la tabla entera, y eso -por el riesgo
que tiene sobre datos ya guardados- se escribe a mano donde toque, no aquí.
"""

from __future__ import annotations

import sqlite3


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    fila = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return fila is not None


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Nombres de las columnas que tiene la tabla ahora mismo."""
    # PRAGMA no admite parámetros enlazados, de ahí la interpolación; `table`
    # nunca viene de fuera del programa (son literales de logic/schema.py).
    # El nombre se lee por posición (columna 1 de table_info) y no por clave,
    # para funcionar igual con o sin `row_factory`.
    return {fila[1] for fila in conn.execute(f"PRAGMA table_info({table})")}


def add_column_if_missing(
    conn: sqlite3.Connection, table: str, column: str, definition: str
) -> bool:
    """Añade `column` a `table` si no la tiene ya. Devuelve si la ha añadido.

    `definition` es el trozo de DDL que va tras el nombre, tal cual se
    escribiría en el CREATE TABLE ("TEXT NOT NULL DEFAULT ''"). SQLite exige
    que una columna NOT NULL añadida a posteriori traiga DEFAULT: no hay otra
    forma de rellenar las filas que ya existen.

    Idempotente: llamarla en cada arranque no cuesta nada -es una lectura del
    esquema- y es lo que permite que `ensure_tables()` siga siendo el único
    sitio del que se acuerda nadie.
    """
    if not table_exists(conn, table) or column in table_columns(conn, table):
        return False

    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return True
