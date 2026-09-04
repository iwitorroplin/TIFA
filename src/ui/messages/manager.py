from PySide6.QtCore import QObject, Signal

from src.ui.messages.messages import Message
from src.ui.messages.types import MessageType, Module


class MessageManager(QObject):
    """Punto central por el que cualquier módulo emite un Message.

    No se instancia por módulo: se usa la instancia compartida `manager`
    de este archivo, así ninguna vista necesita recibirla por constructor.
    Guarda todo en `history` aunque nadie esté mirando cuando se emite.
    """

    messagePushed = Signal(Message)

    def __init__(self):
        super().__init__()
        self._history: list[Message] = []

    def push(self, module: Module, type: MessageType, text: str) -> Message:
        message = Message(module=module, type=type, text=text)
        self._history.append(message)
        self.messagePushed.emit(message)
        return message

    @property
    def history(self) -> list[Message]:
        return list(self._history)


# Instancia compartida: `from src.ui.messages.manager import manager`.
manager = MessageManager()
