from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.db.connection import connect
from src.logic.steriflow.backup.robocopy import run_robocopy
from src.logic.steriflow.config import AutoclaveConfig, SteriflowSettings
from src.logic.steriflow.logs.logger import Logger
from src.logic.steriflow.network import is_reachable
from src.logic.steriflow.sterilization import service as sterilization_service

_LOG_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


class BackupService:
    """`fetch()` y `backup()` son las dos mitades del pipeline, invocables por
    separado (p. ej. desde la interfaz) para que una autoclave apagada nunca
    impida replicar al servidor lo que ya había en local, ni al revés. `run()`
    es lo que dispara el `Scheduler` automático: las dos mitades seguidas,
    sobre un único log de ejecución."""

    def __init__(self, settings: SteriflowSettings) -> None:
        self._settings = settings

    def run(self) -> None:
        logger = self._new_logger()
        logger.log("PASO 0: Prepara la carpeta de logs y el archivo de log de esta ejecución")
        self._fetch_all(logger)
        self._backup_all(logger)
        logger.log("Backup Steriflow finalizado")

    def fetch(self) -> None:
        """Acción manual: solo trae los PDF nuevos de las autoclaves a su carpeta local."""
        logger = self._new_logger()
        logger.log("PASO 0: Prepara la carpeta de logs y el archivo de log de esta ejecución")
        self._fetch_all(logger)
        logger.log("Traída desde las máquinas finalizada")

    def backup(self) -> None:
        """Acción manual: solo replica lo que ya hay en local hacia el servidor de cada autoclave."""
        logger = self._new_logger()
        logger.log("PASO 0: Prepara la carpeta de logs y el archivo de log de esta ejecución")
        self._backup_all(logger)
        logger.log("Backup a servidor finalizado")

    def _new_logger(self) -> Logger:
        timestamp = datetime.now().strftime(_LOG_TIMESTAMP_FORMAT)
        log_file = self._settings.paths.logs_root / f"steriflow_backup_{timestamp}.log"
        return Logger(log_file)

    def _fetch_all(self, logger: Logger) -> None:
        for autoclave in self._settings.autoclaves:
            if not autoclave.active:
                logger.log(f"[{autoclave.name}] Inactiva, se omite")
                continue
            try:
                self._fetch_autoclave(autoclave, logger)
            except Exception as ex:
                logger.log(f"[{autoclave.name}] ERROR trayendo PDF de la autoclave: {ex}")

    def _backup_all(self, logger: Logger) -> None:
        # Una única conexión para todo el backup: se abre y se cierra aquí en
        # vez de en cada autoclave, y en este hilo -nunca el de la interfaz-,
        # que es el único que la usa (ver `BackupRunner`).
        conn = connect()
        try:
            for autoclave in self._settings.autoclaves:
                if not autoclave.active:
                    logger.log(f"[{autoclave.name}] Inactiva, se omite")
                    continue
                try:
                    self._backup_autoclave(autoclave, logger, conn)
                except Exception as ex:
                    logger.log(f"[{autoclave.name}] ERROR replicando hacia el servidor: {ex}")
        finally:
            conn.close()

    def _fetch_autoclave(self, autoclave: AutoclaveConfig, logger: Logger) -> None:
        local_path = Path(autoclave.local_folder)

        logger.log(f"[{autoclave.name}] PASO 1: asegura la carpeta local de staging")
        local_path.mkdir(parents=True, exist_ok=True)

        logger.log(f"[{autoclave.name}] Comprobando conexión con {autoclave.ip}...")
        if not autoclave.path_folder.strip():
            logger.log(f"[{autoclave.name}] Sin carpeta de origen configurada, se omite la copia desde la autoclave")
        elif is_reachable(autoclave.ip):
            logger.log(
                f"[{autoclave.name}] PASO 3: trae los PDF desde {autoclave.path_folder} "
                f"a la carpeta local de staging"
            )
            # Destino como string crudo, no str(local_path): igual que con
            # path_folder, Path le añadiría una barra final a un recurso pelado.
            run_robocopy(autoclave.path_folder, autoclave.local_folder, "*.pdf", logger)
        else:
            logger.log(
                f"[{autoclave.name}] Sin conexión con {autoclave.ip}, se omite la copia "
                f"desde {autoclave.path_folder}"
            )

    def _backup_autoclave(self, autoclave: AutoclaveConfig, logger: Logger, conn) -> None:
        local_path = Path(autoclave.local_folder)
        server_path = Path(autoclave.backup_folder)

        logger.log(f"[{autoclave.name}] PASO 2: asegura la carpeta de servidor")
        server_path.mkdir(parents=True, exist_ok=True)

        logger.log(f"[{autoclave.name}] PASO 4: detecta informes nuevos desde el último backup")
        nuevos = self._find_new_reports(local_path, server_path)
        if nuevos:
            logger.log(f"[{autoclave.name}] {len(nuevos)} informe(s) nuevo(s):")
            for pdf in nuevos:
                logger.log(f"[{autoclave.name}]   {pdf.relative_to(local_path)}")
        else:
            logger.log(f"[{autoclave.name}] Sin informes nuevos")

        logger.log(f"[{autoclave.name}] PASO 5: replica lo local hacia el servidor")
        # Destino como string crudo, no str(server_path): igual que con
        # path_folder, Path le añadiría una barra final a un recurso pelado.
        run_robocopy(autoclave.local_folder, autoclave.backup_folder, "*.pdf", logger)

        logger.log(f"[{autoclave.name}] PASO 6: extrae el dato de esterilización de los PDF nuevos")
        sterilization_service.process(conn, autoclave.name, local_path, server_path, logger)

    @staticmethod
    def _find_new_reports(local_path: Path, server_path: Path) -> list[Path]:
        """PDF que ya están en el staging local pero todavía no en el servidor.

        El servidor solo se replica hacia (nunca se purga, ver `run_robocopy`),
        así que su contenido es el historial de lo ya respaldado: lo que hay en
        local y no en servidor es justo lo llegado desde la autoclave en este
        backup o en uno anterior que no llegó a replicar.
        """
        if not local_path.is_dir():
            return []
        ya_en_servidor = (
            {p.relative_to(server_path) for p in server_path.rglob("*.pdf")}
            if server_path.is_dir() else set()
        )
        return sorted(
            (p for p in local_path.rglob("*.pdf") if p.relative_to(local_path) not in ya_en_servidor),
            key=lambda p: p.relative_to(local_path),
        )
