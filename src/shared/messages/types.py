from enum import Enum


class MessageType(Enum):
    """Severidad de un mensaje que un personaje dice en voz alta. Determina
    quién lo dice y de qué color se tiñe (ver src/shared/characters/senders.py):
    info -> Yufi, success -> Tifa, warning -> Cloud, error -> Sephiroth.

    No hay severidad "silenciosa" (antes DEBUG): un detalle interno no es un
    Message, es una línea de log -`Logger.log(texto)` sin `talk`-.
    """

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Module(Enum):
    """Módulo que origina un mensaje. Los mismos nombres que usan Navbar y
    LogsView para sus pestañas, más `APP` para lo que no es de ningún módulo:
    un fallo no controlado, la limpieza de logs del arranque (ver
    src/app/housekeeping.py).
    """

    APP = "app"
    HOME = "home"
    FERLO = "ferlo"
    STERIFLOW = "steriflow"
    MACONA = "macona"
    PASTEURIZATION = "pasteurization"
    CONFIG = "config"
    LOGS = "logs"
    PRUEBA_UI = "prueba_ui"
