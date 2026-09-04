


from enum import Enum

# Tipo de mensaje para la interfaz de usuario
# Los haremos como si los personajes de home lo dijeran
# añadiremos una interfaz de vista para que el usuario pueda ver los mensajes de la aplicación

# info lo mandara yufi
# success lo mandara tifa
# warning lo mandara cloud
# error lo mandara sephiroth
# ver la relacion tipo -> personaje en messages.py

class MessageType(Enum):

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# Módulo que origina un mensaje (ver Message en messages.py). Los mismos
# nombres que usan Navbar y LogsView para sus pestañas.
class Module(Enum):

    HOME = "home"
    FERLO = "ferlo"
    STERIFLOW = "steriflow"
    MACONA = "macona"
    PASTEURIZATION = "pasteurization"
    CONFIG = "config"
    LOGS = "logs"