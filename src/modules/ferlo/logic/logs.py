"""Dónde y cómo escribe Ferlo sus logs. Única factoría de `Logger` del
módulo, igual que `src/modules/steriflow/logic/logs.py`.
"""

from __future__ import annotations

from pathlib import Path

from src.shared.logs.logger import Logger
from src.shared.messages.types import Module
from src.shared.paths import LOGS_DIR

FERLO_LOGS_ROOT = LOGS_DIR / "ferlo"
AGENT_LOG_FILENAME = "ferlo_agent.log"


def agent_log_path() -> Path:
    return FERLO_LOGS_ROOT / AGENT_LOG_FILENAME


def agent_logger() -> Logger:
    return Logger(agent_log_path(), Module.FERLO)
