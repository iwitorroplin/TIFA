from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QButtonGroup, QVBoxLayout, QWidget

from src.shared.assets.resources import (
    APP_ICON,
)
from src.shared.ui.components.nav_button import add_nav_button as _add_nav_button


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
        return _add_nav_button(
            self._layout,
            self._group,
            label,
            icon=icon,
            color=color,
            checkable=checkable,
            callback=callback,
        )
