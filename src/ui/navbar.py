from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QButtonGroup, QVBoxLayout, QWidget

from src.ui.assets import (
    APP_ICON,
)
from src.ui.components.nav_button import NavButton


class Navbar(QWidget):
    currentChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(160)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.currentChanged)

        # Solo "Home" lleva un icono propio (el logo de la app, fijo); el
        # resto usa el punto "materia" que NavButton colorea según el estado.
        self.add_nav_button("Home", APP_ICON, color="#3f51b5")
        self.add_nav_button("Ferlo")
        self.add_nav_button("Steriflow")
        self.add_nav_button("Macona")
        self.add_nav_button("Pasteurization")
        self.add_nav_button("Configuración")
        self.add_nav_button("Logs")
        self.add_nav_button("Prueba UI")
        self.add_nav_button("Salir",color="#ca4646", callback=QApplication.quit)

    def add_nav_button(self, label, icon=None, color=None, checkable=True, callback=None):
        """Un solo punto de entrada para los botones del navbar.

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
            self._layout.addWidget(button)
            return button

        index = len(self._group.buttons())
        self._group.addButton(button, index)
        self._layout.insertWidget(index, button)

        if index == 0:
            button.setChecked(True)

        return button
