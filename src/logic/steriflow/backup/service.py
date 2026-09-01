from __future__ import annotations

import subprocess
from datetime import datetime

from src.logic.steriflow.backup.robocopy import run_robocopy
from src.logic.steriflow.config import AutoclaveConfig, SteriflowSettings
from src.logic.steriflow.logs.logger import Logger

_PING_TIMEOUT_MS = 2000
_LOG_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


class BackupService:
    def __init__(self, settings: SteriflowSettings) -> None:
        self._settings = settings

    def run(self) -> None:
        timestamp = datetime.now().strftime(_LOG_TIMESTAMP_FORMAT)
        log_file = self._settings.paths.logs_root / f"steriflow_backup_{timestamp}.log"
        logger = Logger(log_file)

        logger.log("PASO 0: Prepara la carpeta de logs y el archivo de log de esta ejecución")

        for autoclave in self._settings.autoclaves:
            if not autoclave.active:
                logger.log(f"[{autoclave.name}] Inactiva, se omite")
                continue

            try:
                self._process_autoclave(autoclave, logger)
            except Exception as ex:
                logger.log(f"[{autoclave.name}] ERROR inesperado, se continúa con las demás autoclaves: {ex}")

        logger.log("Backup Steriflow finalizado")

    def _process_autoclave(self, autoclave: AutoclaveConfig, logger: Logger) -> None:
        local_path = self._settings.paths.local_root / autoclave.name
        server_path = self._settings.paths.server_root / autoclave.name

        # Las dos mitades se aislan: un problema con el servidor de trazabilidad no debe
        # impedir traer los PDF de la autoclave, ni viceversa.
        try:
            logger.log(f"[{autoclave.name}] PASO 1: asegura la carpeta local de staging")
            local_path.mkdir(parents=True, exist_ok=True)

            logger.log(f"[{autoclave.name}] Comprobando conexión con {autoclave.ip}...")
            if self._is_reachable(autoclave.ip):
                logger.log(f"[{autoclave.name}] PASO 3: trae los PDF de la autoclave a la carpeta local de staging")
                source = fr"\\{autoclave.name}\Export"
                run_robocopy(source, str(local_path), "*.pdf", logger)
            else:
                logger.log(f"[{autoclave.name}] Sin conexión con {autoclave.ip}, se omite la copia desde la autoclave")
        except Exception as ex:
            logger.log(f"[{autoclave.name}] ERROR trayendo PDF de la autoclave: {ex}")

        try:
            logger.log(f"[{autoclave.name}] PASO 2: asegura la carpeta de servidor")
            server_path.mkdir(parents=True, exist_ok=True)

            logger.log(f"[{autoclave.name}] PASO 4: replica lo local hacia el servidor")
            run_robocopy(str(local_path), str(server_path), "*.pdf", logger)
        except Exception as ex:
            logger.log(f"[{autoclave.name}] ERROR replicando hacia el servidor: {ex}")

    @staticmethod
    def _is_reachable(ip_address: str) -> bool:
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(_PING_TIMEOUT_MS), ip_address],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return result.returncode == 0
        except OSError:
            return False
