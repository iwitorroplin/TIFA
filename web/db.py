"""Apertura de la base de datos compartida desde la parte web.

No es un paquete con esquema propio -eso vive en cada `web/modules/<x>/db.py`,
junto a su tabla, no aquí-. Esto es solo el punto único que delega en
`src.shared.db.connection.connect`, para que ningún fichero de `web/` importe
esa función directamente y sea sencillo ver, en un solo sitio, qué toca la
parte web de una base de datos que también usa la app de escritorio.
"""

from __future__ import annotations

import sqlite3

from src.shared.db.connection import connect


def open_conn() -> sqlite3.Connection:
    """Conexión a `data/tifa.db`, con el esquema de todos los módulos de
    `web/registry.py` ya registrado (import perezoso: evita el ciclo
    `web.db` -> `web.registry` -> `web.modules.*` -> `web.db`).

    Ábrela en el hilo que la vaya a usar y ciérrala tú mismo -no se comparte
    entre hilos, misma regla que en `src/modules/steriflow/logic/backup/service.py`
    y `.../ui/data_page.py`.
    """
    import web.registry  # noqa: F401

    return connect()
