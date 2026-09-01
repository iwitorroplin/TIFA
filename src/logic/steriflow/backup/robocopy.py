from __future__ import annotations

import subprocess

from src.logic.steriflow.logs.logger import Logger


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
        f"/LOG+:{logger.log_file_path}",
    ]

    result = subprocess.run(args, creationflags=subprocess.CREATE_NO_WINDOW)

    # Códigos 0-7 = éxito (incluye "sin cambios"); 8+ = hubo fallos. Ver robocopy /?.
    exit_code = result.returncode
    if exit_code >= 8:
        logger.log(f"ERROR robocopy [{source} -> {destination}] código de salida {exit_code}")
    else:
        logger.log(f"OK robocopy [{source} -> {destination}] código de salida {exit_code}")

    return exit_code
