"""Lo que la aplicación hace al arrancar y nadie le pide: recoger los logs
viejos y ponerse la red de seguridad para los fallos que nadie ha previsto.

Vive en `src/app/` y no en `shared/` porque recorre el registro de módulos:
es composition root, igual que `registry.py`.
"""

from __future__ import annotations

import sys
import threading
import traceback

from src.modules.registry import MODULES
from src.shared.config import app_config
from src.shared.logs.logger import Logger
from src.shared.logs.retention import purge_old_logs
from src.shared.messages.types import MessageType, Module
# Log de la aplicación en sí (`APP_LOG_PATH`), para lo que no es de ningún
# módulo: un fallo no controlado puede saltar en cualquier parte, incluso antes
# de que exista una ventana donde enseñarlo.
from src.shared.paths import APP_LOG_PATH


def app_logger() -> Logger:
    return Logger(APP_LOG_PATH, Module.APP)


def purge_module_logs() -> None:
    """Borra los logs que pasen de la antigüedad configurada, en la carpeta de
    cada módulo que tenga log y en la de la propia app.

    No avisa con ningún personaje aunque borre cien ficheros: es tarea
    rutinaria de arranque, y un popup nada más abrir la aplicación es justo lo
    que este sistema de mensajes intenta no ser. Queda escrito en el log de
    cada módulo, que es donde se mira.
    """
    months = app_config.load_settings().logs_retention_months

    for logger, directory in _log_directories():
        borrados, fallidos = purge_old_logs(directory, months)
        if borrados:
            logger.log(f"Limpieza de logs: {borrados} fichero(s) de más de {months} mes(es) borrados")
        if fallidos:
            logger.log(f"Limpieza de logs: {fallidos} fichero(s) no se pudieron borrar")


def _log_directories():
    """(logger, carpeta) de cada log que la app mantiene. Los módulos salen del
    registro, así que uno nuevo entra en la limpieza en cuanto declare su
    `log_path` -sin tocar este fichero-."""
    pairs = [(app_logger(), APP_LOG_PATH.parent)]

    for spec in MODULES:
        if spec.log_path is None:
            continue
        try:
            path = spec.log_path()
        except Exception as ex:
            app_logger().log(f"No se pudo localizar el log de {spec.label}: {ex}")
            continue
        pairs.append((Logger(path, spec.id), path.parent))

    return pairs


def install_crash_handler() -> None:
    """Deja constancia de los fallos que nadie captura, en vez de perderlos.

    Sin esto van a stderr, que en una app de ventanas (o empaquetada, sin
    consola) no lo lee nadie: el fallo desaparece sin dejar rastro. Se cubren
    los dos caminos, el hilo principal y los hilos de trabajo -el backup corre
    en uno de ellos-.
    """
    sys.excepthook = _log_unhandled
    threading.excepthook = _log_unhandled_in_thread


def _log_unhandled(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    detalle = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    # El mensaje que se dice es corto; el volcado entero solo al log.
    app_logger().log(f"FALLO NO CONTROLADO\n{detalle}")
    app_logger().log(
        f"Fallo no controlado ({exc_type.__name__}): {exc_value}. El detalle está en {APP_LOG_PATH}",
        talk=MessageType.ERROR,
    )


def _log_unhandled_in_thread(args) -> None:
    _log_unhandled(args.exc_type, args.exc_value, args.exc_traceback)
