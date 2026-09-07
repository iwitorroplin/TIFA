"""Comprobar si las autoclaves están disponibles y si tienen datos nuevos, y
dejarlo escrito en el log.

Entre backup y backup nadie sabe si una autoclave estuvo apagada media tarde:
el log solo habla de los momentos en que tocaba copiar. Esta comprobación
rellena ese hueco mientras la automatización está encendida (`AvailabilityMonitor`)
y también justo antes de cada backup manual, para que quede constancia del
estado de las máquinas en el momento de lanzarlo.

No dispara ni cancela ningún backup: solo mira y anota. Una máquina disponible
pero sin datos nuevos tampoco necesita que se haga nada — que no hiciera falta
copiar nada también es un dato que interesa tener registrado.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from src.modules.steriflow.logic.backup.reports import new_reports
from src.modules.steriflow.logic.config import AutoclaveConfig, SteriflowSettings
from src.modules.steriflow.logic.network import MachineStatus, check_machine_status
from src.shared.logs.logger import Logger

# Media hora: lo bastante fino para ver cuándo se cayó una autoclave y lo
# bastante espaciado para no llenar el log ni estar pingando todo el rato.
CHECK_INTERVAL_S = 30 * 60

_STATUS_TEXT = {
    MachineStatus.ONLINE: "disponible",
    MachineStatus.OFFLINE: "NO disponible (apagada o fuera de la red)",
    MachineStatus.CONNECTION_ERROR: "sin respuesta (motivo desconocido: red, firewall...)",
}


@dataclass(frozen=True)
class AutoclaveAvailability:
    """Foto de una autoclave en un instante: si responde y qué tiene pendiente.

    Los dos contadores valen None cuando no se pudo mirar — la máquina no
    responde, o la carpeta no se dejó leer—, que no es lo mismo que un cero.
    """

    name: str
    status: MachineStatus
    # Informes en la autoclave que aún no están en la carpeta local.
    pending_fetch: int | None
    # Informes en la carpeta local que aún no están en el servidor.
    pending_backup: int | None

    @property
    def is_available(self) -> bool:
        return self.status is MachineStatus.ONLINE

    @property
    def has_new_data(self) -> bool:
        return bool(self.pending_fetch) or bool(self.pending_backup)

    def describe(self) -> str:
        """La línea tal cual va al log."""
        partes = [_STATUS_TEXT[self.status]]

        if self.is_available and not self.has_new_data and self.pending_fetch is not None:
            partes.append("sin datos nuevos, no hace falta backup")
        else:
            partes.append(_pending_text("por traer de la máquina", self.pending_fetch))
            partes.append(_pending_text("por replicar al servidor", self.pending_backup))

        return f"[{self.name}] {' · '.join(partes)}"


def _pending_text(what: str, value: int | None) -> str:
    return f"{what}: sin comprobar" if value is None else f"{what}: {value}"


def check_autoclave(autoclave: AutoclaveConfig) -> AutoclaveAvailability:
    """Un ping (hasta 2 s, ver `check_machine_status`) y un vistazo a las carpetas."""
    status = check_machine_status(autoclave.ip)

    # La carpeta de la autoclave solo se mira si la máquina responde: si está
    # apagada, listar su recurso de red se queda esperando al timeout de SMB,
    # que es mucho más largo que el del ping.
    pending_fetch = None
    if status is MachineStatus.ONLINE and autoclave.path_folder.strip():
        pending_fetch = _count_new_reports(
            Path(autoclave.path_folder), Path(autoclave.local_folder)
        )

    pending_backup = _count_new_reports(
        Path(autoclave.local_folder), Path(autoclave.backup_folder)
    )

    return AutoclaveAvailability(autoclave.name, status, pending_fetch, pending_backup)


def _count_new_reports(source: Path, target: Path) -> int | None:
    try:
        return len(new_reports(source, target))
    except OSError:
        # Comprobar es solo para tener constancia: si una carpeta de red no se
        # deja leer se anota como "no se pudo mirar" y se sigue con el resto.
        return None


def check_all(settings: SteriflowSettings) -> list[AutoclaveAvailability]:
    """Comprueba las autoclaves activas, en orden de configuración."""
    return [check_autoclave(a) for a in settings.autoclaves if a.active]


def log_availability(settings: SteriflowSettings, logger: Logger, reason: str) -> list[AutoclaveAvailability]:
    """Comprueba y escribe el resultado en el log. `reason` dice qué lo motivó
    (la ronda periódica, un backup manual...) para poder seguirlo después."""
    logger.log(f"Comprobando disponibilidad de las autoclaves ({reason})")

    resultados = check_all(settings)
    if not resultados:
        logger.log("No hay ninguna autoclave activa que comprobar")
        return resultados

    for resultado in resultados:
        logger.log(resultado.describe())
    return resultados


class AvailabilityMonitor:
    """Ronda periódica de comprobación mientras la automatización está activa.

    Vive en su propio hilo, igual que el `Scheduler`, y se para con él: si el
    usuario apaga los backups automáticos, la app deja también de sondear las
    máquinas.
    """

    def __init__(
        self,
        settings: SteriflowSettings,
        logger: Logger,
        interval_s: float = CHECK_INTERVAL_S,
    ) -> None:
        self._settings = settings
        self._logger = logger
        self._interval_s = interval_s
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                log_availability(self._settings, self._logger, "ronda automática")
            except Exception as ex:
                # Un fallo comprobando no puede matar el hilo: se anota y se
                # espera a la siguiente ronda.
                self._logger.log(f"ERROR comprobando la disponibilidad de las autoclaves: {ex}")

            if self._stop_event.wait(self._interval_s):
                break
