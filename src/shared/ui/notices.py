from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from src.shared.messages.notice import Notice
from src.shared.messages.types import MessageType

_DEFAULT_TITLE = "Aviso"

_ICONS = {
    MessageType.INFO: QMessageBox.information,
    MessageType.SUCCESS: QMessageBox.information,
    MessageType.WARNING: QMessageBox.warning,
    MessageType.ERROR: QMessageBox.critical,
}


def show(parent: QWidget | None, notice: Notice) -> None:
    """Un `Notice` como diálogo modal síncrono. Para lo que es respuesta a un
    formulario y debe interrumpir -no para lo que ya se anuncia por
    `src.shared.messages.notice.announce`/`push`, que no bloquea."""
    _ICONS[notice.type](parent, notice.title or _DEFAULT_TITLE, notice.text)
