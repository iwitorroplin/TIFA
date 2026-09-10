"""Vacía la tabla `steriflow_backup_file`: el registro de qué PDF ya se
respaldó y se leyó.

No toca ningún PDF. Vaciarla hace que el siguiente backup vuelva a registrar
y a leer todos los informes que haya en las carpetas, así que es la forma de
reprocesarlos con un lector nuevo (medido: ~0,2 s por PDF).

Para regenerar además los ciclos ya guardados, vacía también la otra tabla:

    python tools/wipe_steriflow_backup_file.py
    python tools/wipe_steriflow_cycle.py

Uso: python tools/wipe_steriflow_backup_file.py [--yes]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.modules.steriflow.logic.logs import agent_logger  # noqa: E402
from src.modules.steriflow.logic.schema import ensure_tables  # noqa: E402
from tools._wipe import wipe  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(
        wipe(
            "steriflow_backup_file",
            what="el registro de qué PDF ya estaban respaldados y leídos "
                 "(el siguiente backup los volverá a leer todos)",
            ensure_tables=ensure_tables,
            logger_factory=agent_logger,
        )
    )
