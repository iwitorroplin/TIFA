"""Todo lo relativo a dónde y cómo escribe Steriflow sus logs: ni el
controller (que orquesta scheduler y monitor) ni config.py (que es
configuración de usuario) son el sitio de esto -ver el comentario de
STERIFLOW_LOGS_ROOT más abajo-. Juntarlo aquí deja una única factoría de
Logger para todo el módulo, en vez de que cada fichero de ui/ construya el
suyo por separado.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.shared.logs.logger import Logger
from src.shared.messages.types import Module
from src.shared.paths import LOGS_DIR

# Antes venía de steriflowConfig.yaml (`logs_root`), editable desde la
# pestaña de Configuración. Se fija aquí -igual que DB_PATH en
# src/shared/db/connection.py- porque el log es lo que explica qué pasó tras
# un fallo: no debe poder quedar apuntando a una ruta que el usuario cambió o
# borró sin querer.
STERIFLOW_LOGS_ROOT = LOGS_DIR / "steriflow"

AGENT_LOG_FILENAME = "steriflow_agent.log"
# Prefijo de los ficheros de log de cada ejecución de backup (uno por
# corrida). Debe coincidir con el que usa new_backup_log_path(): si alguna
# vez difieren, "Último backup" y la pestaña Logs dejan de encontrar las
# ejecuciones en silencio.
BACKUP_LOG_PREFIX = "steriflow_backup_"

_LOG_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


def agent_log_path() -> Path:
    return STERIFLOW_LOGS_ROOT / AGENT_LOG_FILENAME


def new_backup_log_path(moment: datetime | None = None) -> Path:
    timestamp = (moment or datetime.now()).strftime(_LOG_TIMESTAMP_FORMAT)
    return STERIFLOW_LOGS_ROOT / f"{BACKUP_LOG_PREFIX}{timestamp}.log"


def agent_logger() -> Logger:
    return Logger(agent_log_path(), Module.STERIFLOW)


def new_backup_logger() -> Logger:
    return Logger(new_backup_log_path(), Module.STERIFLOW)
