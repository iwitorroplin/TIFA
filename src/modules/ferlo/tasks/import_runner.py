from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal

from src.modules.ferlo.logic.controller import FerloController


class ImportRunner(QObject):
    """Corre una acción de Ferlo (check, importar, reanalizar) en un hilo
    aparte para no congelar la interfaz mientras se relee un CSV de ~225.000
    filas.

    Mismo patrón que `src/modules/steriflow/tasks/backup_runner.py`: la acción
    corre fuera del hilo de Qt (no puede tocar widgets directamente) y solo
    avisa con señales, que Qt entrega ya en el hilo de la interfaz. Un guard
    propio (`_busy`) evita que dos acciones corran a la vez -no hay guard
    compartido con nada más porque Ferlo no tiene automatización (D4): la única
    otra forma de escribir es `logic/ingest/cli.py`, un proceso aparte.

    Es agnóstico de qué acción corre: recibe el callable y devuelve lo que
    salga por `finished`. Quien lo llama decide qué anunciar -así el check, que
    no cambia nada, no tiene que fingir que produce un resumen de importación.
    """

    started = Signal()
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, controller: FerloController) -> None:
        super().__init__()
        self._controller = controller
        self._lock = threading.Lock()
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    def run(self, action: Callable[[], object]) -> bool:
        """Devuelve False sin lanzar nada si ya hay una acción en curso."""
        with self._lock:
            if self._busy:
                return False
            self._busy = True

        self.started.emit()
        threading.Thread(target=self._worker, args=(action,), daemon=True).start()
        return True

    def _worker(self, action: Callable[[], object]) -> None:
        try:
            result = action()
        except Exception as ex:  # noqa: BLE001 - se emite y no se relanza: no hay quien lo capture en el hilo de Qt
            self.failed.emit(ex)
        else:
            self.finished.emit(result)
        finally:
            with self._lock:
                self._busy = False
