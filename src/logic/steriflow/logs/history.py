from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# Cada ejecución deja un archivo steriflow_backup_<AAAAMMDD>_<HHMMSS>.log en la carpeta
# de logs, así que el nombre del más reciente ya dice cuándo fue el último backup. Leerlo
# del disco (en vez de recordarlo en memoria) hace que el dato sobreviva a reinicios de
# la app. El log del agente (steriflow_agent.log) no matchea este patrón.
_LOG_NAME = re.compile(r"^steriflow_backup_(\d{8}_\d{6})\.log$")
_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


def list_backup_logs(logs_directory: Path) -> list[tuple[datetime, Path]]:
    """Todos los logs de backup con su fecha/hora (leída del nombre, no del
    mtime), más reciente primero."""
    try:
        entries = list(logs_directory.glob("steriflow_backup_*.log"))
    except OSError:
        return []

    parsed: list[tuple[datetime, Path]] = []
    for entry in entries:
        match = _LOG_NAME.match(entry.name)
        if match is None:
            continue

        try:
            moment = datetime.strptime(match.group(1), _TIMESTAMP_FORMAT)
        except ValueError:
            continue

        parsed.append((moment, entry))

    return sorted(parsed, key=lambda item: item[0], reverse=True)


def last_backup_time(logs_directory: Path) -> datetime | None:
    """Cuándo fue el último backup, o None si todavía no corrió ninguno."""
    entries = list_backup_logs(logs_directory)
    return entries[0][0] if entries else None
