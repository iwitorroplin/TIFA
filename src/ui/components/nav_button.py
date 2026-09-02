from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

from src.ui.assets import (
    MATERIA_BLUE_ICON,
    MATERIA_YELLOW_ICON,
    )

# MATERIA BLUE PARA BOTON STANDAR
# MATERIA YELLOW PARA BOTON CON HOVER o CHECKED



class NavButton(QPushButton):
    def __init__(
            self,
            text,
            icon=None,
            color=None,
            checkable=True):

        super().__init__(text)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(20, 20))

        # Un icono propio (p. ej. el logo en "Home") se queda fijo siempre;
        # sin icono, el botón usa el punto "materia" que cambia de color
        # según el estado (ver comentario de arriba).
        self._fixed_icon = icon is not None
        self._icon_standard = QIcon(str(icon if icon is not None else MATERIA_BLUE_ICON))
        self._icon_active = self._icon_standard if self._fixed_icon else QIcon(str(MATERIA_YELLOW_ICON))
        self.setIcon(self._icon_standard)
        self.toggled.connect(self._update_icon)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        base = QColor(color or "#595f66")
        default = base.name()
        hover = base.lighter(140).name()
        checked = base.darker(140).name()

        self.setStyleSheet(
            f"""
            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                text-align: left;
                background-color: {default};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:checked {{
                background-color: {checked};
            }}
            """
        )

    def enterEvent(self, event):
        super().enterEvent(event)
        self._update_icon()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._update_icon()

    def _update_icon(self, *_):
        if self._fixed_icon:
            return
        active = self.underMouse() or self.isChecked()
        self.setIcon(self._icon_active if active else self._icon_standard)