"""Ejecuta el backup de Steriflow cada vez que llega una de las horas programadas."""

from __future__ import annotations

import threading
from datetime import datetime, time, timedelta
from typing import Callable, Iterable

from src.modules.steriflow.messages import catalog
from src.shared.logs.logger import Logger
from src.shared.messages.notice import announce


class Scheduler:
    def __init__(self, execution_hours: Iterable[time], on_execute: Callable[[], None], logger: Logger) -> None:
        self._execution_hours = sorted(execution_hours)
        if not self._execution_hours:
            raise ValueError("execution_hours no puede estar vacío")

        self._on_execute = on_execute
        self._logger = logger
        self._stop_event = threading.Event()
        self._next_execution: datetime | None = None

    @property
    def next_execution(self) -> datetime | None:
        """Cuándo toca el próximo backup programado, para poder mostrarlo en la interfaz."""
        return self._next_execution

    def stop(self) -> None:
        self._stop_event.set()
        self._next_execution = None

    def run(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now()
            next_time = next((t for t in self._execution_hours if t > now.time()), self._execution_hours[0])

            next_datetime = datetime.combine(now.date(), next_time)
            if next_datetime <= now:
                next_datetime += timedelta(days=1)

            delay = (next_datetime - now).total_seconds()
            self._next_execution = next_datetime
            self._logger.log(f"Siguiente ejecución: {next_datetime:%Y-%m-%d %H:%M:%S}")

            if self._stop_event.wait(delay):
                break

            self._logger.log("Iniciando backup Steriflow...")
            try:
                self._on_execute()
            except Exception as ex:
                # Unico sitio del modulo donde algo puede fallar sin nadie
                # delante: si esto solo se anotara, un backup nocturno roto no
                # se descubriria hasta que alguien abriese el log.
                announce(self._logger, catalog.scheduled_backup_failed(ex))
