from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from src.modules.steriflow.logic.controller import SteriflowController
from src.modules.steriflow.logic.logs import agent_logger
from src.shared.logs.logger import Logger
from src.shared.messages.types import MessageType


class BackupRunner(QObject):
    """Dispara acciones de backup manuales en un hilo aparte para no congelar la interfaz.

    La acción corre fuera del hilo de Qt, así que no puede tocar widgets directamente:
    avisa con señales, que Qt entrega ya en el hilo de la interfaz. Comparte el guard
    del controller con el scheduler, así que nunca corren dos acciones a la vez
    (tanto entre sí como con la ejecución programada).

    Lo que se le dice al usuario no viaja por estas señales: lo dice el log con
    `talk=` -la acción anuncia su propio final, y aquí solo se anuncian los dos
    casos que la acción no puede contar (que ni siquiera llegó a arrancar, y que
    reventó a media ejecución)-. Las señales solo sirven para habilitar y
    deshabilitar botones.
    """

    started = Signal()
    # Termine bien o mal: la interfaz reacciona igual (reactivar botones).
    finished = Signal()

    def __init__(self, controller: SteriflowController) -> None:
        super().__init__()
        self._controller = controller

    def run(self, source: str, action: Optional[Callable[[], None]] = None) -> bool:
        """Lanza `action` (por defecto, el pipeline completo) en segundo plano.

        Devuelve False si ya había una acción en curso (y no dispara otra).
        """
        logger = agent_logger()

        if not self._controller.try_start_run_now():
            logger.log(
                f"Backup manual desde {source} ignorado: ya hay una acción en curso",
                talk=MessageType.WARNING,
            )
            return False

        run_action = action or self._controller.backup_service.run
        logger.log(f"Backup manual iniciado desde {source}")
        self.started.emit()
        threading.Thread(
            target=self._worker, args=(logger, run_action), daemon=True
        ).start()
        return True

    def _worker(self, logger: Logger, action: Callable[[], None]) -> None:
        self._log_availability(logger)
        try:
            # El "terminado" lo dice la propia acción (ver BackupService), que
            # es la que sabe qué mitad del pipeline acaba de correr.
            action()
        except Exception as ex:
            logger.log(f"ERROR en backup manual: {ex}", talk=MessageType.ERROR)
        finally:
            self._controller.finish_run_now()
            self.finished.emit()

    def _log_availability(self, logger: Logger) -> None:
        """Anota cómo estaban las máquinas al lanzar el backup: si luego no se
        copia nada, en el log queda si fue porque alguna no respondía o porque
        no había datos nuevos.

        Comprobar es solo para tener constancia, así que si la comprobación
        falla se deja dicho y el backup sigue igual.
        """
        try:
            self._controller.log_availability("backup manual")
        except Exception as ex:
            logger.log(f"No se pudo comprobar la disponibilidad de las autoclaves: {ex}")
