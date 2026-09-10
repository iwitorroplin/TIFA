from __future__ import annotations

import subprocess

from src.shared.logs.logger import Logger
from src.shared.messages.types import MessageType


def run_robocopy(source: str, destination: str, file_mask: str, logger: Logger) -> int:
    args = [
        "robocopy",
        source,
        destination,
        file_mask,
        "/E",
        "/R:3",
        "/W:5",
        "/NFL",
        "/NDL",
        "/NP",
    ]

    # Antes se volcaba con /LOG+: directo al fichero de log de la ejecución:
    # metía ahí, cientos de veces al día, la cabecera y tabla nativas de
    # robocopy -sin marca de tiempo, con su propio formato- rompiendo la
    # homogeneidad del resto del log (una línea `[fecha hora] mensaje` por
    # evento). Se captura en memoria en su lugar: en éxito no hace falta -la
    # línea OK/ERROR de abajo ya lo dice-, y en fallo de verdad se reescribe
    # línea a línea con el mismo formato que el resto del log.
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
        text=True,
        errors="replace",
    )

    # Códigos 0-7 = éxito (incluye "sin cambios"); 8+ = hubo fallos. Ver robocopy /?.
    #
    # El resultado va con nivel (SUCCESS/ERROR) y no como un "OK"/"ERROR"
    # dentro del texto: así esta línea se lee y se filtra igual que las demás
    # del log, que es lo que antes rompía -era la única línea del backup sin
    # nivel ni autoclave-. El ámbito lo pone el logger que llega (ver
    # `Logger.scoped` en backup/service.py).
    exit_code = result.returncode
    if exit_code >= 8:
        logger.log(
            f"robocopy [{source} -> {destination}] código de salida {exit_code}",
            level=MessageType.ERROR,
        )
        for line in _relevant_lines(result.stdout):
            logger.log(f"  {line}", level=MessageType.ERROR)
    else:
        logger.log(
            f"robocopy [{source} -> {destination}] código de salida {exit_code}",
            level=MessageType.SUCCESS,
        )

    return exit_code


def _relevant_lines(output: str) -> list[str]:
    """Lo que queda de la salida nativa de robocopy quitando el ruido puramente
    decorativo (separadores, líneas en blanco): con /NFL /NDL puestos, es la
    tabla resumen y, si las hay, sus líneas ERROR -justo lo que hace falta
    para no tener que repetir la copia a mano solo para ver qué falló."""
    return [
        line.strip()
        for line in output.splitlines()
        if line.strip() and not line.lstrip().startswith("---")
    ]
