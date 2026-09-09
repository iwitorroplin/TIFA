"""Importa y analiza Ferlo sin abrir la aplicación.

    python -m src.modules.ferlo.logic.ingest.cli [MAQUINA ...]

Con la parte web aplazada (ver el documento de la Fase 0 del port), es la
única forma de comprobar la ruta diaria sin la ventana: la herramienta con la
que se depura todo lo que toca `logic/ingest/` y `logic/analysis/`.
"""

from __future__ import annotations

import argparse
import sqlite3

from src.modules.ferlo.logic.config import load_settings
from src.modules.ferlo.logic.schema import ensure_tables
from src.shared.db.connection import DB_PATH

from .service import import_machine

MACHINES = ["F1", "F2", "F3", "F4", "F5"]


def _connect() -> sqlite3.Connection:
    """Conexión directa a `tifa.db`, con solo el esquema de Ferlo -este
    script no abre el resto de la app, así que no necesita el de los demás
    módulos-."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_tables(conn)
    return conn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "machine", nargs="*", choices=MACHINES,
        help="Máquina(s) a importar; sin argumentos, las cinco.",
    )
    args = parser.parse_args(argv)
    machines = args.machine or MACHINES

    settings = load_settings()
    conn = _connect()
    try:
        for machine in machines:
            resumen = import_machine(conn, settings, machine)
            if not resumen.arrivals:
                print(f"{machine}: nada pendiente en la entrada")
                continue
            print(
                f"{machine}: {len(resumen.arrivals)} llegada(s), "
                f"{resumen.total_new_rows} filas nuevas, {resumen.total_cycles} ciclos"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
