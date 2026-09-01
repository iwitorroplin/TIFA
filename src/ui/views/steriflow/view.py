from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from src.ui.views.steriflow.home_page import SteriflowHomePage
from src.ui.views.steriflow.tab_bar import SteriflowTabBar


class SteriflowView(QWidget):
    def __init__(self):
        super().__init__()

        self._tabs = SteriflowTabBar()
        self._pages = QStackedWidget()
        self._pages.addWidget(SteriflowHomePage())
        self._pages.addWidget(self._placeholder_page("Steriflow - Configuración"))
        self._pages.addWidget(self._placeholder_page("Steriflow - Data"))
        self._pages.addWidget(self._placeholder_page("Steriflow - Logs"))

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)

    def _placeholder_page(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
