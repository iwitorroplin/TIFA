from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from src.modules.steriflow.logic.controller import AGENT_LOG_FILENAME, SteriflowController
from src.shared.logs.logger import Logger


class BackupRunner(QObject):
    """Dispara acciones de backup manuales en un hilo aparte para no congelar la interfaz.

    La acción corre fuera del hilo de Qt, así que no puede tocar widgets directamente:
    avisa con señales, que Qt entrega ya en el hilo de la interfaz. Comparte el guard
    del controller con el scheduler, así que nunca corren dos acciones a la vez
    (tanto entre sí como con la ejecución programada).
    """

    started = Signal()
    finished = Signal(str)
    failed = Signal(str)
    already_running = Signal()

    def __init__(self, controller: SteriflowController) -> None:
        super().__init__()
        self._controller = controller

    def run(
        self,
        source: str,
        action: Optional[Callable[[], None]] = None,
        done_message: str = "Backup finalizado.",
    ) -> bool:
        """Lanza `action` (por defecto, el pipeline completo) en segundo plano.

        Devuelve False si ya había una acción en curso (y no dispara otra).
        """
        if not self._controller.try_start_run_now():
            self.already_running.emit()
            return False

        run_action = action or self._controller.backup_service.run
        agent_logger = Logger(self._controller.settings.paths.logs_root / AGENT_LOG_FILENAME)
        agent_logger.log(f"Backup manual iniciado desde {source}")
        self.started.emit()
        threading.Thread(
            target=self._worker, args=(agent_logger, run_action, done_message), daemon=True
        ).start()
        return True

    def _worker(self, agent_logger: Logger, action: Callable[[], None], done_message: str) -> None:
        try:
            action()
            self.finished.emit(done_message)
        except Exception as ex:
            agent_logger.log(f"ERROR en backup manual: {ex}")
            self.failed.emit(f"Error durante el backup: {ex}")
        finally:
            self._controller.finish_run_now()
