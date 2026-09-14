from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QVBoxLayout,
    QWidget
)

from src.modules.registry import MODULES
from src.shared.assets.paths import ACTION_SETTING, NAV_HOME, NAV_MODULE
from src.shared.messages.types import Module
from src.shared.ui.components.nav_button import NavExitButton, add_nav_button as _add_nav_button

# Apariencia (icono/color) del botón de nav de cada módulo. registry.py solo
# describe módulos (id, view, logs); esto es presentación pura del navbar, y
# vive aquí porque Navbar es su único consumidor. Un módulo ausente aquí cae
# al icono/color por defecto de NavButton.
_NAV_STYLE: dict[Module, tuple] = {
    Module.HOME: (NAV_HOME, None),
    Module.FERLO: (NAV_MODULE, None),
    Module.STERIFLOW: (NAV_MODULE, None),
    Module.MACONA: (NAV_MODULE, None),
    Module.PASTEURIZATION: (NAV_MODULE, None),
    Module.CONFIG: (ACTION_SETTING, None),
}


class Navbar(QWidget):
    currentChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(160)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(10)
        self._layout.addStretch()

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.currentChanged)

        # Un botón por módulo registrado, en su mismo orden (ver
        # src/modules/registry.py); MainWindow apila sus páginas con el
        # mismo recorrido, así que el índice de cada botón siempre coincide

        for spec in MODULES:
            icon, color = _NAV_STYLE.get(spec.id, (None, None))
            self.add_nav_button(spec.label, icon, color=color)

        exit_button = NavExitButton(QApplication.quit)
        self._layout.addWidget(exit_button)

    def add_nav_button(self, label, icon=None, color=None):
        return _add_nav_button(
            self._layout,
            self._group,
            label,
            icon=icon,
            color=color,
        )
