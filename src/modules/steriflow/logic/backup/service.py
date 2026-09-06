from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.shared.db.connection import connect
from src.modules.steriflow.logic.backup.reports import new_reports
from src.modules.steriflow.logic.backup.robocopy import run_robocopy
from src.modules.steriflow.logic.config import AutoclaveConfig, SteriflowSettings
from src.shared.logs.logger import Logger
from src.shared.messages.types import MessageType, Module
from src.modules.steriflow.logic.network import is_reachable
from src.modules.steriflow.logic.sterilization import service as sterilization_service

_LOG_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# robocopy: 0-7 es exito (incluye "sin cambios"), 8+ es fallo. Ver robocopy /?.
_ROBOCOPY_FAILURE_CODE = 8


class BackupService:
    """`fetch()` y `backup()` son las dos mitades del pipeline, invocables por
    separado (p. ej. desde la interfaz) para que una autoclave apagada nunca
    impida replicar al servidor lo que ya había en local, ni al revés. `run()`
    es lo que dispara el `Scheduler` automático: las dos mitades seguidas,
    sobre un único log de ejecución.

    Cada acción anuncia su propio final con `talk=` (una línea de log de las
    cientos que escribe): es la que sabe qué acaba de correr, así el aviso al
    usuario sale igual venga de un botón o del scheduler de las 3 de la
    mañana, sin que la interfaz tenga que repetir el texto."""

    def __init__(self, settings: SteriflowSettings) -> None:
        self._settings = settings

    def run(self) -> None:
        logger = self._new_logger()
        logger.log("PASO 0: Prepara la carpeta de logs y el archivo de log de esta ejecución")
        incidencias = self._fetch_all(logger) + self._backup_all(logger)
        self._announce_end(logger, "Backup Steriflow finalizado", incidencias)

    def fetch(self) -> None:
        """Acción manual: solo trae los PDF nuevos de las autoclaves a su carpeta local."""
        logger = self._new_logger()
        logger.log("PASO 0: Prepara la carpeta de logs y el archivo de log de esta ejecución")
        incidencias = self._fetch_all(logger)
        self._announce_end(logger, "Traída desde las máquinas finalizada", incidencias)

    def backup(self) -> None:
        """Acción manual: solo replica lo que ya hay en local hacia el servidor de cada autoclave."""
        logger = self._new_logger()
        logger.log("PASO 0: Prepara la carpeta de logs y el archivo de log de esta ejecución")
        incidencias = self._backup_all(logger)
        self._announce_end(logger, "Backup a servidor finalizado", incidencias)

    def _announce_end(self, logger: Logger, done_message: str, incidencias: int) -> None:
        """El único mensaje que ve el usuario de toda la ejecución, y tiene que
        decir la verdad: un fallo con una autoclave no corta el pipeline -una
        máquina apagada no debe impedir copiar el resto-, así que sin contarlos
        un SUCCESS en verde taparía media copia sin hacer.

        Cuenta solo fallos de verdad (una excepción, o robocopy devolviendo 8 o
        más). Una autoclave inactiva, apagada o sin carpeta de origen es un
        salto previsto, no una incidencia: si contara, casi todas las noches
        acabarían en WARNING y el aviso dejaría de significar nada.
        """
        if incidencias:
            logger.log(
                f"{done_message}, con {incidencias} incidencia(s): ver el detalle más arriba en este log",
                talk=MessageType.WARNING,
            )
        else:
            logger.log(done_message, talk=MessageType.SUCCESS)

    def _new_logger(self) -> Logger:
        timestamp = datetime.now().strftime(_LOG_TIMESTAMP_FORMAT)
        log_file = self._settings.paths.logs_root / f"steriflow_backup_{timestamp}.log"
        return Logger(log_file, Module.STERIFLOW)

    def _fetch_all(self, logger: Logger) -> int:
        """Devuelve cuántas autoclaves fallaron (ver `_announce_end`)."""
        incidencias = 0
        for autoclave in self._settings.autoclaves:
            if not autoclave.active:
                logger.log(f"[{autoclave.name}] Inactiva, se omite")
                continue
            try:
                incidencias += self._fetch_autoclave(autoclave, logger)
            except Exception as ex:
                logger.log(f"[{autoclave.name}] ERROR trayendo PDF de la autoclave: {ex}")
                incidencias += 1
        return incidencias

    def _backup_all(self, logger: Logger) -> int:
        """Devuelve cuántas autoclaves fallaron (ver `_announce_end`)."""
        # Una única conexión para todo el backup: se abre y se cierra aquí en
        # vez de en cada autoclave, y en este hilo -nunca el de la interfaz-,
        # que es el único que la usa (ver `BackupRunner`).
        incidencias = 0
        conn = connect()
        try:
            for autoclave in self._settings.autoclaves:
                if not autoclave.active:
                    logger.log(f"[{autoclave.name}] Inactiva, se omite")
                    continue
                try:
                    incidencias += self._backup_autoclave(autoclave, logger, conn)
                except Exception as ex:
                    logger.log(f"[{autoclave.name}] ERROR replicando hacia el servidor: {ex}")
                    incidencias += 1
        finally:
            conn.close()
        return incidencias

    def _fetch_autoclave(self, autoclave: AutoclaveConfig, logger: Logger) -> int:
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
            # robocopy no lanza excepción: devuelve código, y un 8+ es un fallo
            # que hasta ahora solo se veía leyendo el log a mano.
            codigo = run_robocopy(autoclave.path_folder, autoclave.local_folder, "*.pdf", logger)
            return 1 if codigo >= _ROBOCOPY_FAILURE_CODE else 0
        else:
            logger.log(
                f"[{autoclave.name}] Sin conexión con {autoclave.ip}, se omite la copia "
                f"desde {autoclave.path_folder}"
            )

        return 0

    def _backup_autoclave(self, autoclave: AutoclaveConfig, logger: Logger, conn) -> int:
        local_path = Path(autoclave.local_folder)
        server_path = Path(autoclave.backup_folder)

        logger.log(f"[{autoclave.name}] PASO 2: asegura la carpeta de servidor")
        server_path.mkdir(parents=True, exist_ok=True)

        logger.log(f"[{autoclave.name}] PASO 4: detecta informes nuevos desde el último backup")
        nuevos = new_reports(local_path, server_path)
        if nuevos:
            logger.log(f"[{autoclave.name}] {len(nuevos)} informe(s) nuevo(s):")
            for pdf in nuevos:
                logger.log(f"[{autoclave.name}]   {pdf.relative_to(local_path)}")
        else:
            logger.log(f"[{autoclave.name}] Sin informes nuevos")

        logger.log(f"[{autoclave.name}] PASO 5: replica lo local hacia el servidor")
        # Destino como string crudo, no str(server_path): igual que con
        # path_folder, Path le añadiría una barra final a un recurso pelado.
        codigo = run_robocopy(autoclave.local_folder, autoclave.backup_folder, "*.pdf", logger)

        logger.log(f"[{autoclave.name}] PASO 6: extrae el dato de esterilización de los PDF nuevos")
        # Un PDF que no se deja leer no cuenta como incidencia de la copia:
        # queda marcado con su error en la base de datos (`repo.mark_extracted`)
        # y se reintenta; el backup en sí fue bien.
        sterilization_service.process(conn, autoclave.name, local_path, server_path, logger)

        return 1 if codigo >= _ROBOCOPY_FAILURE_CODE else 0
