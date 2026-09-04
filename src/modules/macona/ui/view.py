from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from src.modules.macona.ui.tab_bar import MaconaTabBar


class MaconaView(QWidget):
    def __init__(self):
        super().__init__()

        self._tabs = MaconaTabBar()
        self._pages = QStackedWidget()
        self._pages.addWidget(self._placeholder_page("Macona - Tab 1"))
        self._pages.addWidget(self._placeholder_page("Macona - Tab 2"))

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)

    def _placeholder_page(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
