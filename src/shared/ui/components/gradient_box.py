from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

# Mismo aspecto que los cuadros de personaje (ver characters/message_box.py):
# marco blanco redondeado con relleno en degradado azul -> negro. Extraído
# aquí, sin nada de personajes ni mensajes, para poder reutilizar solo el
# cuadro en cualquier panel de la app -p.ej. el cuadro de bienvenida de Home-.
_BORDER_COLOR = QColor("#ffffff")
_BORDER_WIDTH = 5
_OUTER_RADIUS = 14
_INNER_RADIUS = 9


class GradientBox(QWidget):
    """Cuadro con marco blanco y relleno en degradado azul -> negro, sin
    contenido propio: quien lo use le pone su layout encima, igual que a
    cualquier QWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        outer_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_BORDER_COLOR)
        painter.drawRoundedRect(outer_rect, _OUTER_RADIUS, _OUTER_RADIUS)

        inner_rect = outer_rect.adjusted(
            _BORDER_WIDTH, _BORDER_WIDTH, -_BORDER_WIDTH, -_BORDER_WIDTH
        )

        gradient = QLinearGradient(0, inner_rect.top(), 0, inner_rect.bottom())
        gradient.setColorAt(0.0, QColor("#17366f"))
        gradient.setColorAt(0.45, QColor("#0b1d40"))
        gradient.setColorAt(1.0, QColor("#000000"))

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(inner_rect, _INNER_RADIUS, _INNER_RADIUS)

        super().paintEvent(event)
