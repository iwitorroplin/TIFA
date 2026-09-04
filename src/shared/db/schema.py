"""Punto único donde cada módulo registra sus tablas.

Este paquete no conoce a ningún módulo concreto (evita el ciclo
shared -> module -> shared): cada módulo registra su propia función de
esquema con `register_schema` durante el arranque de la app (ver
`src/modules/registry.py`), antes de que se abra la primera conexión.
"""

from __future__ import annotations

import sqlite3
from typing import Callable

SchemaFn = Callable[[sqlite3.Connection], None]

_REGISTRY: list[SchemaFn] = []


def register_schema(fn: SchemaFn) -> SchemaFn:
    _REGISTRY.append(fn)
    return fn


def ensure_schema(conn: sqlite3.Connection) -> None:
    for fn in _REGISTRY:
        fn(conn)
