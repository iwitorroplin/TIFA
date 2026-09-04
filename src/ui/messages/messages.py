from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from src.shared.assets.resources import CLOUD, SEPHIROTH, TIFA, YUFI
from src.ui.messages.types import MessageType, Module


@dataclass(frozen=True)
class MessageSender:
    """Personaje que envía un mensaje: nombre + retrato."""

    name: str
    portrait: Path


@dataclass(frozen=True)
class Message:
    """Mensaje real emitido por un módulo, con quién lo originó y cuándo.

    El remitente (personaje) y el color se resuelven aparte a partir de
    `type` vía SENDERS/ACCENT_COLORS: son fijos por severidad, no por
    módulo (ver readme del planteamiento en memoria del proyecto).
    """

    module: Module
    type: MessageType
    text: str
    timestamp: datetime = field(default_factory=datetime.now)


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


# Los retratos (assets/images/characters/*.svg) son solo dos colores: fondo
# blanco ("background") y tinta negra ("shape"). En vez de mantener un SVG
# por personaje y color, se retiñe el fondo en tiempo real.
_WHITE_FILL = "fill:#ffffff"




def tinted_portrait(sender: MessageSender, color: QColor, size: int) -> QPixmap:
    """Retrato de `sender` con el fondo teñido de `color`, a tamaño `size`x`size`."""

    svg_data = sender.portrait.read_text(encoding="utf-8")
    svg_data = svg_data.replace(_WHITE_FILL, f"fill:{color.name()}")

    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap
