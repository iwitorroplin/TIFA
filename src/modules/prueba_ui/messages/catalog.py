"""Catálogo de mensajes de prueba de prueba_ui: al ser un sandbox sin
eventos de negocio reales, no tiene sentido inventar una función por evento
(como tendría un módulo real, p. ej. backup_ok()); hay un texto de ejemplo
por severidad y una única función parametrizada que empuja el que se pida,
igual que hace un módulo real contra `manager`.
"""

from src.shared.messages.manager import manager
from src.shared.messages.message import Message
from src.shared.messages.types import Delivery, MessageType, Module

_TEXTS: dict[MessageType, str] = {
    MessageType.INFO: "Mensaje de prueba: esto es solo información.",
    MessageType.SUCCESS: "Mensaje de prueba: la operación de ejemplo salió bien.",
    MessageType.WARNING: "Mensaje de prueba: revisa esto, aunque no es grave.",
    MessageType.ERROR: "Mensaje de prueba: algo ha fallado en el ejemplo. Y es MUY LARRRRRRRRRRRRRGOOOOOOOOOOOOOOOOOOOOO"
    "",
    MessageType.DEBUG: "Mensaje de prueba: detalle interno, sin personaje asignado.",
}


def send_test_message(
    message_type: MessageType, delivery: Delivery = Delivery.CHARACTER
) -> Message:
    return manager.push(Module.PRUEBA_UI, message_type, _TEXTS[message_type], delivery=delivery)
