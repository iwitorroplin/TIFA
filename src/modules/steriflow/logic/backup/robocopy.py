from __future__ import annotations

import subprocess

from src.shared.logs.logger import Logger


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
    exit_code = result.returncode
    if exit_code >= 8:
        logger.log(f"ERROR robocopy [{source} -> {destination}] código de salida {exit_code}")
        for line in _relevant_lines(result.stdout):
            logger.log(f"  {line}")
    else:
        logger.log(f"OK robocopy [{source} -> {destination}] código de salida {exit_code}")

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
