from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal

from src.modules.ferlo.logic.controller import FerloController
from src.modules.ferlo.logic.ingest.service import ImportSummary
from src.modules.ferlo.logic.logs import agent_logger
from src.modules.ferlo.messages import catalog
from src.shared.messages.notice import announce


class ImportRunner(QObject):
    """Lanza `controller.import_machine(machine)` en un hilo aparte para no
    congelar la interfaz mientras se relee un CSV de ~225.000 filas.

    Mismo patrón que `src/modules/steriflow/tasks/backup_runner.py`: la
    acción corre fuera del hilo de Qt (no puede tocar widgets directamente) y
    solo avisa con señales, que Qt entrega ya en el hilo de la interfaz. Un
    guard propio (`_busy`) evita que dos importaciones corran a la vez -no
    hay guard compartido con nada más porque Ferlo no tiene automatización
    (D4): la única otra forma de escribir es `logic/ingest/cli.py`, un
    proceso aparte."""

    started = Signal()
    # (machine, summary): el resumen es lo que pinta la página al terminar.
    finished = Signal(str, object)
    failed = Signal(str, object)

    def __init__(self, controller: FerloController) -> None:
        super().__init__()
        self._controller = controller
        self._lock = threading.Lock()
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    def run(self, machine: str) -> bool:
        """Devuelve False sin lanzar nada si ya hay una importación en curso."""
        with self._lock:
            if self._busy:
                return False
            self._busy = True

        self.started.emit()
        threading.Thread(target=self._worker, args=(machine,), daemon=True).start()
        return True

    def _worker(self, machine: str) -> None:
        logger = agent_logger()
        try:
            summary: ImportSummary = self._controller.import_machine(machine)
        except Exception as ex:  # noqa: BLE001 - se anuncia y no se relanza: no hay quien lo capture en el hilo de Qt
            announce(logger, catalog.import_failed(machine, ex))
            self.failed.emit(machine, ex)
        else:
            announce(logger, catalog.import_finished(machine, summary))
            self.finished.emit(machine, summary)
        finally:
            with self._lock:
                self._busy = False
