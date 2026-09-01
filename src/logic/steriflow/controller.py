from __future__ import annotations

import threading
from datetime import datetime

from src.logic.steriflow.backup.scheduler import Scheduler
from src.logic.steriflow.backup.service import BackupService
from src.logic.steriflow.config import SteriflowSettings, ensure_config_file, load_settings
from src.logic.steriflow.logs.history import last_backup_time
from src.logic.steriflow.logs.logger import Logger

_AGENT_LOG_FILENAME = "steriflow_agent.log"


class SteriflowController:
    """Mantiene viva la configuración de Steriflow y su scheduler, y permite
    recargarlos desde disco (por ejemplo, tras guardar cambios en la pestaña de
    configuración) sin tener que reiniciar la app."""

    def __init__(self, settings: SteriflowSettings) -> None:
        self._lock = threading.Lock()
        self._scheduler: Scheduler | None = None
        self._run_now_lock = threading.Lock()
        self._run_now_in_progress = False

        self.settings = settings
        self.backup_service = BackupService(settings)

    def try_start_run_now(self) -> bool:
        """Marca un backup manual como 'en curso'. Devuelve False si ya hay uno
        corriendo, para que nunca corran dos backups al mismo tiempo."""
        with self._run_now_lock:
            if self._run_now_in_progress:
                return False
            self._run_now_in_progress = True
            return True

    def finish_run_now(self) -> None:
        with self._run_now_lock:
            self._run_now_in_progress = False

    @property
    def last_backup(self) -> datetime | None:
        """Cuándo terminó el último backup, deducido de los logs en disco."""
        return last_backup_time(self.settings.paths.logs_root)

    @property
    def next_execution(self) -> datetime | None:
        """Cuándo toca el próximo backup programado (None si el scheduler está parado)."""
        scheduler = self._scheduler
        return scheduler.next_execution if scheduler is not None else None

    def start(self) -> None:
        with self._lock:
            self._start_scheduler_locked()

    def reload(self) -> None:
        with self._lock:
            self.settings = load_settings()
            self.backup_service = BackupService(self.settings)

            if self._scheduler is not None:
                self._scheduler.stop()

            self._start_scheduler_locked()

    def stop(self) -> None:
        """Solo detiene el scheduler: no cancela un backup manual en curso."""
        with self._lock:
            if self._scheduler is not None:
                self._scheduler.stop()

    def _start_scheduler_locked(self) -> None:
        agent_logger = Logger(self.settings.paths.logs_root / _AGENT_LOG_FILENAME)
        scheduler = Scheduler(
            self.settings.schedule.execution_hours,
            self.backup_service.run,
            agent_logger,
        )
        self._scheduler = scheduler
        threading.Thread(target=scheduler.run, daemon=True).start()


def build_default_controller() -> SteriflowController:
    ensure_config_file()
    return SteriflowController(load_settings())
