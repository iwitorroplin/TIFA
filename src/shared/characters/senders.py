from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor

from src.shared.assets.resources import CLOUD, SEPHIROTH, TIFA, YUFI
from src.shared.messages.types import MessageType


@dataclass(frozen=True)
class MessageSender:
    """Personaje que envía un mensaje: nombre + retrato."""

    name: str
    portrait: Path


# info -> Yufi
# success -> Tifa
# warning -> Cloud
# error -> Sephiroth
SENDERS: dict[MessageType, MessageSender] = {
    MessageType.INFO: MessageSender("Yufi", YUFI),
    MessageType.SUCCESS: MessageSender("Tifa", TIFA),
    MessageType.WARNING: MessageSender("Cloud", CLOUD),
    MessageType.ERROR: MessageSender("Sephiroth", SEPHIROTH),
}

# Color de acento por tipo de mensaje: tiñe el fondo del retrato, el marco
# del cuadro de diálogo y el nombre del remitente, para reconocer quién
# habla de un vistazo.
ACCENT_COLORS: dict[MessageType, QColor] = {
    MessageType.INFO: QColor("#4fc3f7"),
    MessageType.SUCCESS: QColor("#66bb6a"),
    MessageType.WARNING: QColor("#ffca28"),
    MessageType.ERROR: QColor("#ef5350"),
}
