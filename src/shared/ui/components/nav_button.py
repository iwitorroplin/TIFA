from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

from src.shared.assets.resources import (
    MATERIA_BLUE_IMAGE,
    MATERIA_YELLOW_IMAGE,
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
        self._icon_standard = QIcon(str(icon if icon is not None else MATERIA_BLUE_IMAGE))
        self._icon_active = self._icon_standard if self._fixed_icon else QIcon(str(MATERIA_YELLOW_IMAGE))
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


def add_nav_button(layout, group, label, icon=None, color=None, checkable=True, callback=None):
    """Crea un NavButton y lo añade a `layout`/`group`. Punto de entrada
    compartido por Navbar y TabBar para no repetir el cableado.

    Con `callback` es una acción suelta (p. ej. "Salir"): no entra en el
    grupo exclusivo y se ancla al final, bajo el stretch. Sin `callback`
    es una pestaña de navegación: entra en el grupo exclusivo, se marca
    sola si es la primera, y se inserta antes del stretch.
    """
    is_action = callback is not None
    button = NavButton(
        label,
        icon=icon,
        color=color,
        checkable=False if is_action else checkable,
    )

    if is_action:
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    index = len(group.buttons())
    group.addButton(button, index)
    layout.insertWidget(index, button)

    if index == 0:
        button.setChecked(True)

    return button