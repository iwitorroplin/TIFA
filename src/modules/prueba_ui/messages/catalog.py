"""Catálogo de mensajes de prueba de prueba_ui: al ser un sandbox sin eventos
de negocio reales, no tiene sentido inventar una función por evento (como
tendría un módulo real, p. ej. backup_ok()); hay un texto de ejemplo por
severidad y una única función parametrizada que empuja el que se pida.

Va por `manager.push` y no por `Logger.log(..., talk=...)` porque prueba_ui no
tiene proceso ni log propio que contar: solo sirve para ver a los personajes.
Un módulo real anuncia desde su log (ver `BackupService`).
"""

from src.shared.messages.manager import manager
from src.shared.messages.types import MessageType, Module

_TEXTS: dict[MessageType, str] = {
    MessageType.INFO: "Mensaje de prueba: esto es solo información.",
    MessageType.SUCCESS: "Mensaje de prueba: la operación de ejemplo salió bien.",
    MessageType.WARNING: "Mensaje de prueba: revisa esto, aunque no es grave.",
    MessageType.ERROR: "Mensaje de prueba: algo ha fallado en el ejemplo. Y es MUY "
    "LARRRRRRRRRRRRRGOOOOOOOOOOOOOOOOOOOOO",
}


def send_test_message(message_type: MessageType) -> None:
    manager.push(Module.PRUEBA_UI, message_type, _TEXTS[message_type])
