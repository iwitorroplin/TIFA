from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QButtonGroup, QVBoxLayout, QWidget

from src.ui.assets import APP_ICON
from src.ui.components.sidebar_button import SidebarButton


class Sidebar(QWidget):
    currentChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(160)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #4d88cb;")

        self._placeholder_icon = QIcon(str(APP_ICON))

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.currentChanged)

        self.add_item("Home")
        self.add_item("Configuración")
        self.add_action("Salir", QApplication.quit)

    def add_item(self, label):
        button = SidebarButton(label, icon=self._placeholder_icon)

        index = len(self._group.buttons())
        self._group.addButton(button, index)
        self._layout.insertWidget(index, button)

        if index == 0:
            button.setChecked(True)

        return index

    def add_action(self, label, callback):
        button = SidebarButton(label, icon=self._placeholder_icon, checkable=False)
        button.clicked.connect(callback)
        self._layout.addWidget(button)
