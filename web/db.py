"""
Apertura de la base de datos compartida desde la parte web.

No es un paquete con esquema propio:
-eso vive en cada `web/modules/<x>/db.py` junto a su tabla, no aquí-. 

"""

from __future__ import annotations

import sqlite3

from src.shared.db.connection import connect


def open_conn() -> sqlite3.Connection:
    """
    Conexión a `data/tifa.db`:
    con el esquema de todos los módulos
    `web/registry.py` ya registrado
    import perezoso: evita el ciclo
    `web.db` -> `web.registry` -> `web.modules.*` -> `web.db`

    """
    import web.registry

    return connect()
