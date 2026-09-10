from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from src.shared.messages.manager import manager
from src.shared.messages.types import MessageType, Module


def _to_console(line: str) -> None:
    """Empaquetada con pythonw o como .exe no hay consola: `sys.stdout` es
    None y un print() suelto revienta con AttributeError en cada línea de log
    -el módulo que escribe el historial sería el primero en caerse-."""
    if sys.stdout is None:
        return
    try:
        print(line)
    except (OSError, ValueError):
        pass


class Logger:
    """Escribe el historial de un módulo en su fichero de log y, solo si se le
    pide, hace que además lo diga un personaje.

    Hablar es opt-in (`talk=`) y no al revés: un backup deja cientos de líneas
    de log de las que al usuario le importan una o dos -"terminado", "ha
    fallado"-, así que lo raro es lo que se anuncia, no lo que se calla.

    Toda línea sale con la misma forma, `[fecha] [NIVEL] [ÁMBITO] texto`, para
    que el log se pueda leer -y filtrar con un grep- sin conocer qué función la
    escribió. El ámbito es opcional y se fija una vez con `scoped()` en vez de
    repetirlo a mano en cada f-string.

    Lo escrito aquí es lo que se puede consultar después: la pestaña Logs del
    navbar muestra estos ficheros en vivo. `manager` no guarda nada.
    """

    def __init__(self, log_file_path: Path, module: Module, *, scope: str = "") -> None:
        self.log_file_path = log_file_path
        # Qué módulo firma los mensajes que salgan de este logger con `talk`.
        self.module = module
        # Sobre qué va todo lo que escriba este logger (una autoclave, una
        # máquina...). Vacío = líneas del módulo entero.
        self.scope = scope

        try:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            _to_console(
                f"[{datetime.now():%Y-%m-%d %H:%M:%S}] No se pudo preparar la carpeta "
                f"de logs '{self.log_file_path}': {ex}"
            )

    def scoped(self, scope: str) -> "Logger":
        """Otro logger sobre el mismo fichero y módulo, pero que estampa
        `[scope]` en cada línea. Se usa para recorrer una lista de máquinas sin
        que cada mensaje tenga que acordarse de repetir el prefijo -y sin que
        unos lo pongan delante y otros detrás, como pasaba antes-."""
        return Logger(self.log_file_path, self.module, scope=scope)

    def log(
        self,
        message: str,
        *,
        level: MessageType | None = None,
        talk: MessageType | None = None,
    ) -> None:
        """Anota `message` en el log con su nivel. Con `talk=MessageType.X`,
        además lo dice el personaje de esa severidad (mismo texto: lo que se le
        cuenta al usuario tiene que poder leerse igual luego en el log).

        `level` es el nivel de la línea escrita; si no se dice, lo hereda de
        `talk`, y a falta de los dos es INFO -el caso normal, una línea de
        historial que no reclama nada-.

        Se puede llamar desde un hilo de trabajo: ver `MessageManager`.
        """
        nivel = level or talk or MessageType.INFO
        ambito = f"[{self.scope}] " if self.scope else ""
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{nivel.name}] {ambito}{message}"
        _to_console(line)

        try:
            with self.log_file_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as ex:
            _to_console(
                f"[{datetime.now():%Y-%m-%d %H:%M:%S}] No se pudo escribir en el log "
                f"'{self.log_file_path}': {ex}"
            )

        if talk is not None:
            manager.push(self.module, talk, message)
