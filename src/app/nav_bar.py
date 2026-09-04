from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QButtonGroup, QVBoxLayout, QWidget

from src.modules.registry import MODULES
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

        # Un botón por módulo registrado, en su mismo orden (ver
        # src/modules/registry.py); MainWindow apila sus páginas con el
        # mismo recorrido, así que el índice de cada botón siempre coincide
        # con el de su página sin mantener dos listas a mano.
        for spec in MODULES:
            self.add_nav_button(spec.label, spec.icon, color=spec.color)
        self.add_nav_button("Salir", color="#ca4646", callback=QApplication.quit)

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
