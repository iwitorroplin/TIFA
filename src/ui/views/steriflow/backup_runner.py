from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal

from src.logic.steriflow.controller import SteriflowController
from src.logic.steriflow.logs.logger import Logger

_AGENT_LOG_FILENAME = "steriflow_agent.log"


class BackupRunner(QObject):
    """Dispara backups manuales en un hilo aparte para no congelar la interfaz.

    El backup corre fuera del hilo de Qt, así que no puede tocar widgets directamente:
    avisa con señales, que Qt entrega ya en el hilo de la interfaz. Comparte el guard
    del controller con el scheduler, así que nunca corren dos backups a la vez.
    """

    started = Signal()
    finished = Signal(str)
    already_running = Signal()

    def __init__(self, controller: SteriflowController) -> None:
        super().__init__()
        self._controller = controller

    def run(self, source: str) -> bool:
        """Devuelve False si ya había un backup en curso (y no dispara otro)."""
        if not self._controller.try_start_run_now():
            self.already_running.emit()
            return False

        agent_logger = Logger(self._controller.settings.paths.logs_root / _AGENT_LOG_FILENAME)
        agent_logger.log(f"Backup manual iniciado desde {source}")
        self.started.emit()
        threading.Thread(target=self._worker, args=(agent_logger,), daemon=True).start()
        return True

    def _worker(self, agent_logger: Logger) -> None:
        try:
            self._controller.backup_service.run()
            self.finished.emit("Backup finalizado.")
        except Exception as ex:
            agent_logger.log(f"ERROR en backup manual: {ex}")
            self.finished.emit(f"Error durante el backup: {ex}")
        finally:
            self._controller.finish_run_now()
