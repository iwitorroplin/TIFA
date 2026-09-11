from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton


class NavButton(QPushButton):
    """Base sin elementos por defecto: cada subclase/uso fija su icono y color."""

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

        if icon is not None:
            self.setIcon(QIcon(str(icon)))

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


class NavModuleButton(NavButton):
    """Pestaña de navegación de un módulo: entra en el grupo exclusivo del caller."""

    def __init__(self, label, icon=None, color=None):
        super().__init__(label, icon=icon, color=color, checkable=True)


class NavExitButton(NavButton):
    """Botón de acción "Salir": no es checkable ni entra en el grupo exclusivo."""

    def __init__(self, callback):
        super().__init__("Salir", icon=None, color="#ca4646", checkable=False)
        self.clicked.connect(callback)


def add_nav_button(layout, group, label, icon=None, color=None):
    """
    Crea un NavModuleButton y lo agrega al grupo exclusivo.
    Compartido por Navbar y TabBar.

    Entra en el grupo exclusivo, se marca solo si es el primero,
    y se inserta antes del stretch.
    """
    button = NavModuleButton(label, icon=icon, color=color)

    index = len(group.buttons())
    group.addButton(button, index)
    layout.insertWidget(index, button)

    if index == 0:
        button.setChecked(True)

    return button
