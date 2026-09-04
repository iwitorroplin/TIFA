from PySide6.QtCore import QObject, Signal

from src.shared.messages.message import Message
from src.shared.messages.types import Delivery, MessageType, Module


class MessageManager(QObject):
    """Punto central por el que cualquier módulo emite un Message.

    No se instancia por módulo: se usa la instancia compartida `manager`
    de este archivo, así ninguna vista necesita recibirla por constructor.
    Guarda todo en `history` aunque nadie esté mirando cuando se emite, y
    sea cual sea `delivery` -el auto-cierre o el silencio de un mensaje no
    le hacen perder rastro-.
    """

    messagePushed = Signal(Message)

    def __init__(self):
        super().__init__()
        self._history: list[Message] = []

    def push(
        self,
        module: Module,
        type: MessageType,
        text: str,
        delivery: Delivery = Delivery.CHARACTER,
    ) -> Message:
        # DEBUG es silencioso siempre, sin excepción: ni pasando
        # delivery=CHARACTER se le puede poner un personaje a hablar.
        if type is MessageType.DEBUG:
            delivery = Delivery.SILENT
        message = Message(module=module, type=type, text=text, delivery=delivery)
        self._history.append(message)
        self.messagePushed.emit(message)
        return message

    @property
    def history(self) -> list[Message]:
        return list(self._history)


# Instancia compartida: `from src.shared.messages.manager import manager`.
manager = MessageManager()
