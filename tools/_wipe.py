"""Lo común a los scripts `wipe_<tabla>.py`: vaciar una tabla de `tifa.db`.

Cada tabla tiene su propio script y su nombre va en el fichero, no en un
argumento: así lo que se va a borrar se lee en la línea que se teclea
-`python tools/wipe_steriflow_cycle.py`- y no hay forma de vaciar la tabla
equivocada por un parámetro mal escrito.

Borra FILAS, nunca la tabla: el esquema lo mantiene `ensure_schema()`, y
dejarlo intacto es lo que permite que la aplicación siga arrancando después.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.db.connection import DB_PATH, connect  # noqa: E402
from src.shared.messages.types import MessageType  # noqa: E402


def wipe(
    table: str,
    *,
    what: str,
    ensure_tables=None,
    logger_factory=None,
    argv: list[str] | None = None,
) -> int:
    """Vacía `table` tras confirmarlo por teclado (o con --yes / -y).

    `what` describe en una línea qué se pierde, para que la confirmación diga
    algo más que el nombre de la tabla. `ensure_tables` es la del módulo dueño:
    hace falta llamarla porque `connect()` solo crea el esquema de los módulos
    que la app registra al arrancar (`src/__main__.py`), y aquí no hay app.
    `logger_factory` también es la del módulo: un borrado masivo tiene que
    quedar en su log, que es donde se mira cuando mañana falten datos.
    """
    argv = sys.argv[1:] if argv is None else argv
    sin_preguntar = "--yes" in argv or "-y" in argv

    conn = connect()
    try:
        if ensure_tables is not None:
            ensure_tables(conn)
            conn.commit()
        antes = _count(conn, table)
        print(f"Base de datos: {DB_PATH}")
        print(f"Tabla:         {table}")
        print(f"Filas ahora:   {antes}")
        print(f"Se pierde:     {what}")

        if antes == 0:
            print("\nYa está vacía, no hay nada que borrar.")
            return 0

        if not sin_preguntar and not _confirmado(table):
            print("\nCancelado, no se ha borrado nada.")
            return 1

        conn.execute(f"DELETE FROM {table}")
        conn.commit()
        despues = _count(conn, table)
    finally:
        conn.close()

    print(f"\nBorradas {antes - despues} fila(s). Quedan {despues}.")

    if logger_factory is not None:
        logger_factory().log(
            f"Tabla {table} vaciada a mano con tools/wipe_{table}.py: "
            f"{antes - despues} fila(s) borradas",
            level=MessageType.WARNING,
        )
    return 0


def _count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _confirmado(table: str) -> bool:
    """Pide escribir el nombre de la tabla, no un "s": el borrado no tiene
    vuelta atrás y un sí de una tecla se pulsa sin leer."""
    try:
        respuesta = input(f"\nEscribe '{table}' para confirmar el borrado: ")
    except EOFError:
        # Sin consola interactiva (lanzado desde otro proceso) no hay forma de
        # confirmar: se cancela en vez de borrar por defecto.
        return False
    return respuesta.strip() == table
