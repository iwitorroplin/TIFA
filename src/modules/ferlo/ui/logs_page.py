from __future__ import annotations

from src.modules.ferlo.logic.logs import agent_log_path
from src.shared.ui.components.log_tail_page import LogTailPage


class FerloLogsPage(LogTailPage):
    """Log en vivo de ferlo_agent.log: Ferlo no tiene ejecuciones por corrida
    como Steriflow, solo este único fichero que va creciendo."""

    def __init__(self):
        super().__init__(agent_log_path())
