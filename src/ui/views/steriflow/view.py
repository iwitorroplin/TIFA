from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from src.ui.views.steriflow.tab_bar import SteriflowTabBar


class SteriflowView(QWidget):
    def __init__(self):
        super().__init__()

        self._tabs = SteriflowTabBar()
        self._pages = QStackedWidget()
        self._pages.addWidget(self._placeholder_page("Steriflow - Tab 1"))
        self._pages.addWidget(self._placeholder_page("Steriflow - Tab 2"))

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)

    def _placeholder_page(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
