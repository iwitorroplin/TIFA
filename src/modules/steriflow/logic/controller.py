from __future__ import annotations

import threading
from datetime import datetime

from src.modules.steriflow.logic.backup import availability
from src.modules.steriflow.logic.backup.scheduler import Scheduler
from src.modules.steriflow.logic.backup.service import BackupService
from src.modules.steriflow.logic.config import SteriflowSettings, ensure_config_file, load_settings
from src.shared.logs.history import last_backup_time
from src.shared.logs.logger import Logger
from src.shared.messages.types import Module

AGENT_LOG_FILENAME = "steriflow_agent.log"
BACKUP_LOG_PREFIX = "steriflow_backup_"


class SteriflowController:
    """Mantiene viva la configuración de Steriflow y lo que corre en automático
    —el scheduler de backups y la comprobación periódica de disponibilidad de
    las autoclaves—, y permite recargarlos desde disco (por ejemplo, tras
    guardar cambios en la pestaña de configuración) sin reiniciar la app."""

    def __init__(self, settings: SteriflowSettings) -> None:
        self._lock = threading.Lock()
        self._scheduler: Scheduler | None = None
        self._availability: availability.AvailabilityMonitor | None = None
        self._auto_enabled = False
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
        return last_backup_time(self.settings.paths.logs_root, BACKUP_LOG_PREFIX)

    @property
    def next_execution(self) -> datetime | None:
        """Cuándo toca el próximo backup programado (None si el scheduler está parado)."""
        scheduler = self._scheduler
        return scheduler.next_execution if scheduler is not None else None

    @property
    def auto_enabled(self) -> bool:
        """Si los backups programados por horario están activos o el usuario los paró."""
        return self._auto_enabled

    def start(self) -> None:
        with self._lock:
            self._start_automation_locked()

    def reload(self) -> None:
        with self._lock:
            self.settings = load_settings()
            self.backup_service = BackupService(self.settings)

            self._stop_automation_locked()

            # Recargar config (p. ej. tras guardar en la pestaña de
            # Configuración) no debe reactivar el modo automático si el
            # usuario lo había parado a mano.
            if self._auto_enabled:
                self._start_automation_locked()

    def stop(self) -> None:
        """Para el modo automático: no cancela un backup manual en curso."""
        with self._lock:
            self._stop_automation_locked()
            self._auto_enabled = False

    def log_availability(self, reason: str) -> None:
        """Deja constancia en el log del agente de si las autoclaves responden y
        de si tienen datos nuevos.

        Hace pings y lista carpetas de red, así que tarda: llamarla siempre
        desde un hilo de trabajo, nunca desde el de la interfaz.
        """
        availability.log_availability(self.settings, self._new_agent_logger(), reason)

    def _new_agent_logger(self) -> Logger:
        return Logger(self.settings.paths.logs_root / AGENT_LOG_FILENAME, Module.STERIFLOW)

    def _start_automation_locked(self) -> None:
        """Arranca las dos piezas del modo automático: el que hace los backups a
        sus horas y el que va anotando si las máquinas estaban disponibles entre
        medias."""
        self._stop_automation_locked()

        agent_logger = self._new_agent_logger()
        scheduler = Scheduler(
            self.settings.schedule.execution_hours,
            self.backup_service.run,
            agent_logger,
        )
        monitor = availability.AvailabilityMonitor(self.settings, agent_logger)

        self._scheduler = scheduler
        self._availability = monitor
        self._auto_enabled = True
        threading.Thread(target=scheduler.run, daemon=True).start()
        threading.Thread(target=monitor.run, daemon=True).start()

    def _stop_automation_locked(self) -> None:
        if self._scheduler is not None:
            self._scheduler.stop()
        if self._availability is not None:
            self._availability.stop()
            self._availability = None


def build_default_controller() -> SteriflowController:
    ensure_config_file()
    return SteriflowController(load_settings())
