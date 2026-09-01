from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QButtonGroup, QVBoxLayout, QWidget

from src.ui.assets import (
    APP_ICON,
    MATERIA_BLUE_ICON,
    MATERIA_GREEN_ICON,
    MATERIA_RED_ICON,
    MATERIA_PURPLE_ICON,
    MATERIA_YELLOW_ICON
)
from src.ui.components.nav_button import NavButton


class Navbar(QWidget):
    currentChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(160)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._placeholder_icon = APP_ICON

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.currentChanged)

        self.add_item("Home", APP_ICON)
        self.add_item("Ferlo", MATERIA_RED_ICON)
        self.add_item("Steriflow", MATERIA_RED_ICON)
        self.add_item("Macona", MATERIA_RED_ICON)
        self.add_item("Pasteurization", MATERIA_RED_ICON)
        self.add_item("Configuración", MATERIA_BLUE_ICON)
        self.add_action("Salir", MATERIA_RED_ICON, "#e20c0c", callback=QApplication.quit)

    def add_item(self, label, icon=None, color=None, checkable=True):
        button = NavButton(
            label,
            icon=icon if icon is not None else self._placeholder_icon,
            color=color or "#097cc9",
            checkable=checkable,
        )

        index = len(self._group.buttons())
        self._group.addButton(button, index)
        self._layout.insertWidget(index, button)

        if index == 0:
            button.setChecked(True)

        return index

    def add_action(self, label, icon=None, color=None, callback=None):
        button = NavButton(
            label,
            icon=icon if icon is not None else self._placeholder_icon,
            color=color or "#4d88cb",
            checkable=False,
        )
        button.clicked.connect(callback)
        self._layout.addWidget(button)
