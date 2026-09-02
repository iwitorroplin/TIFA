"""Punto único donde cada módulo registra sus tablas.

Ferlo, Macona y Pasteurización se añaden aquí según vayan teniendo tablas
propias; hasta entonces, solo se crean las de Steriflow.
"""

from __future__ import annotations

import sqlite3

from src.logic.steriflow.schema import ensure_tables as ensure_steriflow_tables


def ensure_schema(conn: sqlite3.Connection) -> None:
    ensure_steriflow_tables(conn)
