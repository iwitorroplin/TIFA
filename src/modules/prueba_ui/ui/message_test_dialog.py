from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout

from src.modules.prueba_ui.messages.catalog import send_test_message
from src.shared.messages.manager import manager
from src.shared.messages.message import Message
from src.shared.messages.types import Delivery, MessageType
from src.shared.ui.components.app_button import AppButton

_BUTTON_LABELS: dict[MessageType, str] = {
    MessageType.INFO: "Info",
    MessageType.SUCCESS: "Success",
    MessageType.WARNING: "Warning",
    MessageType.ERROR: "Error",
}


class MessageTestDialog(QDialog):
    """Sandbox para ver cómo interactúan los personajes: dispara un Message
    por severidad hacia `manager` y registra en un log local todo lo que
    pasa por el bus -incluidos los Delivery.SILENT, que no generan popup y
    si no, parecería que el clic "no hizo nada".

    No modal a propósito (`.show()`, nunca `.exec()`): MessageBox no es una
    ventana top-level propia, es un widget hijo de MainWindow (ver
    MessageBar._on_message_pushed, parent=self.window()). Un exec() aplica
    modal de aplicación y bloquearía toda la ventana principal, incluido el
    botón OK del MessageBox que aparece encima -dejaría de poder cerrarse
    mientras este diálogo sigue abierto.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prueba de mensajes")

        self._silent_checkbox = QCheckBox("Silencioso (sin personaje)")

        button_row = QHBoxLayout()
        for message_type, label in _BUTTON_LABELS.items():
            button = AppButton(label)
            button.clicked.connect(lambda _checked=False, mt=message_type: self._send(mt))
            button_row.addWidget(button)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._silent_checkbox)
        layout.addLayout(button_row)
        layout.addWidget(self._log)

        manager.messagePushed.connect(self._on_message_pushed)

    def _send(self, message_type: MessageType) -> None:
        delivery = Delivery.SILENT if self._silent_checkbox.isChecked() else Delivery.CHARACTER
        send_test_message(message_type, delivery)

    def _on_message_pushed(self, message: Message) -> None:
        self._log.appendPlainText(
            f"[{message.timestamp:%H:%M:%S}] {message.module.value}/{message.type.value}"
            f" ({message.delivery.value}): {message.text}"
        )
