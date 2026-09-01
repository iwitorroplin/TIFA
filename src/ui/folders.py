from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class SupportsLog(Protocol):
    def log(self, message: str) -> None: ...


def open_folder(path: Path, logger: SupportsLog, create: bool = False) -> bool:
    """Abre una carpeta en el explorador. Devuelve False si no se pudo.

    Las carpetas de red (por ejemplo el servidor de trazabilidad) pueden no estar
    disponibles, así que nunca se crean solas: se avisa y listo.
    """
    try:
        if create:
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            logger.log(f"No se pudo abrir '{path}': no existe o no está accesible")
            return False

        os.startfile(path)  # type: ignore[attr-defined]
        return True
    except OSError as ex:
        logger.log(f"No se pudo abrir la carpeta '{path}': {ex}")
        return False
