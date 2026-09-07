from PySide6.QtCore import QObject, Signal

from src.shared.messages.message import Message
from src.shared.messages.types import MessageType, Module


class MessageManager(QObject):
    """Bus por el que pasa lo que un personaje dice en voz alta.

    Es un bus, no un almacén: no guarda historial. Un mensaje que nadie ve en
    el momento se pierde a propósito -el rastro consultable son los ficheros
    de log de cada módulo, que la pestaña Logs del navbar muestra en vivo-.

    No se instancia por módulo: se usa la instancia compartida `manager` de
    este archivo, así ninguna vista necesita recibirla por constructor.

    `push()` es seguro desde un hilo de trabajo: `messagePushed` la recibe
    `MessageBar`, que vive en el hilo de la interfaz, así que Qt entrega la
    llamada encolada en ese hilo (por eso `Logger.log(..., talk=...)` puede
    hablar desde dentro de un backup en segundo plano).
    """

    messagePushed = Signal(Message)

    def push(self, module: Module, type: MessageType, text: str) -> None:
        self.messagePushed.emit(Message(module=module, type=type, text=text))


# Instancia compartida: `from src.shared.messages.manager import manager`.
manager = MessageManager()
