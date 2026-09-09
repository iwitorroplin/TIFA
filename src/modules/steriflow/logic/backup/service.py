from __future__ import annotations

from pathlib import Path

from src.shared.db.connection import connect
from src.modules.steriflow.logic.backup import availability
from src.modules.steriflow.logic.backup.availability import AutoclaveAvailability
from src.modules.steriflow.logic.backup.reports import new_reports
from src.modules.steriflow.logic.backup.robocopy import run_robocopy
from src.modules.steriflow.logic.config import AutoclaveConfig, SteriflowSettings
from src.modules.steriflow.logic.logs import new_backup_logger
from src.modules.steriflow.messages import catalog
from src.shared.logs.logger import Logger
from src.shared.messages.notice import announce
from src.modules.steriflow.logic.sterilization import service as sterilization_service

# robocopy: 0-7 es exito (incluye "sin cambios"), 8+ es fallo. Ver robocopy /?.
_ROBOCOPY_FAILURE_CODE = 8


class BackupService:
    """`fetch()` y `backup()` son las dos mitades del pipeline, invocables por
    separado (p. ej. desde la interfaz) para que una autoclave apagada nunca
    impida replicar al servidor lo que ya había en local, ni al revés. `run()`
    es lo que dispara el `Scheduler` automático: las dos mitades seguidas,
    sobre un único log de ejecución.

    Cada acción anuncia su propio final con `announce()` (`messages/catalog.py`,
    una línea de las cientos que escribe el log): es la que sabe qué acaba de
    correr, así el aviso al usuario sale igual venga de un botón o del
    scheduler de las 3 de la mañana, sin que la interfaz tenga que repetir el
    texto.

    Ese aviso final tiene que decir la verdad: un fallo con una autoclave no
    corta el pipeline -una máquina apagada no debe impedir copiar el resto-,
    así que sin contar las incidencias un SUCCESS en verde taparía media copia
    sin hacer. Solo cuentan fallos de verdad (una excepción, o robocopy
    devolviendo 8 o más); una autoclave inactiva, apagada o sin carpeta de
    origen es un salto previsto, no una incidencia -si contara, casi todas las
    noches acabarían en WARNING y el aviso dejaría de significar nada-."""

    def __init__(self, settings: SteriflowSettings) -> None:
        self._settings = settings

    def run(self) -> None:
        logger = self._new_logger()
        disponibilidad = self._check_availability(logger, "backup automático")
        incidencias = self._fetch_all(logger, disponibilidad) + self._backup_all(logger)
        announce(logger, catalog.full_backup_finished(incidencias))

    def fetch(self) -> None:
        """Acción manual: solo trae los PDF nuevos de las autoclaves a su carpeta local."""
        logger = self._new_logger()
        disponibilidad = self._check_availability(logger, "importación manual")
        incidencias = self._fetch_all(logger, disponibilidad)

        # Sin incidencias pero sin ninguna autoclave disponible no es un
        # SUCCESS silencioso: no se ha traído nada y conviene que se note,
        # en vez de que quede escondido dentro de un "finalizado" en verde.
        if incidencias == 0 and not any(a.is_available for a in disponibilidad.values()):
            announce(logger, catalog.fetch_no_machines_reachable())
        else:
            announce(logger, catalog.fetch_finished(incidencias))

    def backup(self) -> None:
        """Acción manual: solo replica lo que ya hay en local hacia el servidor de cada autoclave."""
        logger = self._new_logger()
        self._check_availability(logger, "exportación manual")
        incidencias = self._backup_all(logger)
        announce(logger, catalog.server_backup_finished(incidencias))

    def _new_logger(self) -> Logger:
        return new_backup_logger()

    def _check_availability(self, logger: Logger, reason: str) -> dict[str, AutoclaveAvailability]:
        """Comprueba una vez si las autoclaves responden y qué tienen
        pendiente, y lo deja en el log. El resultado lo reutiliza
        `_fetch_autoclave` -antes se comprobaba aquí para el log y otra vez,
        por su cuenta, dentro de cada `_fetch_autoclave`: el doble ping podía
        tardar el doble sin motivo."""
        resultados = availability.log_availability(self._settings, logger, reason)
        return {resultado.name: resultado for resultado in resultados}

    def _fetch_all(self, logger: Logger, disponibilidad: dict[str, AutoclaveAvailability]) -> int:
        """Devuelve cuántas autoclaves fallaron: la cuenta que decide si el
        aviso final es SUCCESS o WARNING (ver la clase `BackupService`)."""
        incidencias = 0
        for autoclave in self._settings.autoclaves:
            if not autoclave.active:
                logger.log(f"[{autoclave.name}] Inactiva, se omite")
                continue
            try:
                incidencias += self._fetch_autoclave(autoclave, logger, disponibilidad.get(autoclave.name))
            except Exception as ex:
                logger.log(f"[{autoclave.name}] ERROR trayendo PDF de la autoclave: {ex}")
                incidencias += 1
        return incidencias

    def _backup_all(self, logger: Logger) -> int:
        """Devuelve cuántas autoclaves fallaron: la cuenta que decide si el
        aviso final es SUCCESS o WARNING (ver la clase `BackupService`)."""
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

    def _fetch_autoclave(
        self, autoclave: AutoclaveConfig, logger: Logger, disponibilidad: AutoclaveAvailability | None
    ) -> int:
        local_path = Path(autoclave.local_folder)

        logger.log(f"[INFO] [{autoclave.name}]: Check local_path")
        local_path.mkdir(parents=True, exist_ok=True)

        if not autoclave.path_folder.strip():
            logger.log(f"[{autoclave.name}] Sin carpeta de origen configurada, se omite la copia desde la autoclave")
            return 0

        # 1er check: si no responde -ya comprobado una vez para todas al
        # lanzar la acción, ver _check_availability- no tiene sentido
        # intentar la copia. No se vuelve a pingear aquí.
        if disponibilidad is None or not disponibilidad.is_available:
            logger.log(
                f"[{autoclave.name}] Sin conexión con {autoclave.ip} (comprobado al lanzar la acción), "
                f"se omite la copia desde {autoclave.path_folder}"
            )
            return 0

        # 2º check: si ya está todo traído, invocar robocopy solo para que
        # copie cero ficheros es ruido. `pending_fetch` puede ser None (no se
        # pudo comprobar la carpeta): en ese caso se sigue e intenta, no se
        # asume que no hay nada.
        if disponibilidad.pending_fetch == 0:
            logger.log(f"[{autoclave.name}] Sin informes nuevos en la autoclave, se omite la copia")
            return 0

        logger.log(
            f"[INFO] [{autoclave.name}] : Import PDF {autoclave.path_folder} to {autoclave.local_folder}"

        )
        # Destino como string crudo, no str(local_path): igual que con
        # path_folder, Path le añadiría una barra final a un recurso pelado.
        # robocopy no lanza excepción: devuelve código, y un 8+ es un fallo
        # que hasta ahora solo se veía leyendo el log a mano.
        codigo = run_robocopy(autoclave.path_folder, autoclave.local_folder, "*.pdf", logger)
        return 1 if codigo >= _ROBOCOPY_FAILURE_CODE else 0

    def _backup_autoclave(self, autoclave: AutoclaveConfig, logger: Logger, conn) -> int:
        local_path = Path(autoclave.local_folder)
        server_path = Path(autoclave.backup_folder)

        logger.log(f"[INFO] [{autoclave.name}] : Check {autoclave.backup_folder} asegura la carpeta de servidor")
        server_path.mkdir(parents=True, exist_ok=True)

        logger.log(f"[INFO] [{autoclave.name}] : Check new file")
        nuevos = new_reports(local_path, server_path)
        if nuevos:
            logger.log(f"[{autoclave.name}] {len(nuevos)} pdf(s) new(s):")
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
