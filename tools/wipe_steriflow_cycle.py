"""Vacía la tabla `steriflow_cycle`: los ciclos extraídos de los PDF.

No toca ni los PDF ni `steriflow_backup_file`. Para que los ciclos se vuelvan
a generar hay que vaciar TAMBIÉN el registro de PDF ya leídos, o el siguiente
backup dará por extraído todo lo que ya extrajo:

    python tools/wipe_steriflow_backup_file.py
    python tools/wipe_steriflow_cycle.py

y después lanzar una exportación al servidor desde la aplicación.

Uso: python tools/wipe_steriflow_cycle.py [--yes]
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
            "steriflow_cycle",
            what="los ciclos ya extraídos (fechas, duraciones y temperaturas de esterilización)",
            ensure_tables=ensure_tables,
            logger_factory=agent_logger,
        )
    )
