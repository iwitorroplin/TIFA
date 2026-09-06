from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout

from src.modules.prueba_ui.messages.catalog import send_test_message
from src.shared.messages.manager import manager
from src.shared.messages.message import Message
from src.shared.messages.types import MessageType
from src.shared.ui.components.app_button import AppButton

_BUTTON_LABELS: dict[MessageType, str] = {
    MessageType.INFO: "Info",
    MessageType.SUCCESS: "Success",
    MessageType.WARNING: "Warning",
    MessageType.ERROR: "Error",
}


class MessageTestDialog(QDialog):
    """Sandbox para ver cómo se comportan los personajes: dispara un Message
    por severidad hacia `manager` y anota aquí lo que pasa por el bus.

    Info y Success se cierran solos a los pocos segundos sin bloquear nada;
    Warning y Error bloquean la aplicación hasta el OK (o Esc). El panel de
    abajo no es el historial de la app -ese son los ficheros de log, en la
    pestaña Logs-: es solo para comprobar que un mensaje salió aunque su
    cuadro ya se haya cerrado.

    No modal a propósito (`.show()`, nunca `.exec()`), para poder disparar
    mensajes uno tras otro sin cerrar el sandbox. Un Warning o un Error sí
    bloquean este diálogo mientras estén abiertos: son modales de aplicación
    y se muestran después, así que Qt les da la entrada a ellos.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prueba de mensajes")

        button_row = QHBoxLayout()
        for message_type, label in _BUTTON_LABELS.items():
            button = AppButton(label)
            button.clicked.connect(
                lambda _checked=False, mt=message_type: send_test_message(mt)
            )
            button_row.addWidget(button)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self._log)

        manager.messagePushed.connect(self._on_message_pushed)

    def _on_message_pushed(self, message: Message) -> None:
        self._log.appendPlainText(
            f"[{message.timestamp:%H:%M:%S}] [{message.module.name}] [{message.type.name}] {message.text}"
        )
