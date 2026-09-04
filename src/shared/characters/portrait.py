from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from src.shared.characters.senders import MessageSender

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
