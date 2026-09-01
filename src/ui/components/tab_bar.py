from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QWidget

from src.ui.components.nav_button import NavButton


class TabBar(QWidget):
    currentChanged = Signal(int)

    def __init__(self):
        super().__init__()

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.currentChanged)

    def add_item(self, label, icon=None, color=None):
        button = NavButton(label, icon=icon, color=color or "#4d88cb")

        index = len(self._group.buttons())
        self._group.addButton(button, index)
        self._layout.insertWidget(index, button)

        if index == 0:
            button.setChecked(True)

        return index
