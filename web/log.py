"""Registro de actividad del servidor web, sin usar `src.shared.logs.logger`:
esa clase pasa por `messages/manager.py`, que importa Qt e instancia un
`QObject` a nivel de módulo -coste que este proceso, que nunca abre una
ventana, no tiene por qué pagar-.

Mismo formato de línea que `Logger` para que un log y otro se lean igual, y
la misma firma de fondo (`Callable[[str], None]`) para que el día que el
servidor se lance desde la app de escritorio baste con pasarle
`Logger(ruta, Module.STERIFLOW).log` como `log=` sin tocar `web/server.py`.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.shared.paths import LOGS_DIR

LOG_FILENAME = "tifa_web.log"


def _to_console(line: str) -> None:
    """Sin consola (pythonw, .exe) `sys.stdout` es None; un print() suelto
    tumbaría lo único que deja constancia de que el servidor sigue vivo."""
    if sys.stdout is None:
        return
    try:
        print(line)
    except (OSError, ValueError):
        pass


def make_file_log(log_file_path: Path = LOGS_DIR / LOG_FILENAME) -> Callable[[str], None]:
    """Devuelve una función `log(mensaje)` que escribe a consola y a fichero.

    Función y no clase: lo único que hace falta pasar por ahí es el mensaje,
    y así encaja tal cual en `Callable[[str], None]` sin adaptador.
    """
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        _to_console(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] No se pudo preparar la carpeta de logs '{log_file_path}': {ex}")

    def log(message: str) -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
        _to_console(line)
        try:
            with log_file_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as ex:
            _to_console(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] No se pudo escribir en el log '{log_file_path}': {ex}")

    return log
