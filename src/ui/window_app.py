from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from src.ui.assets import UI_ICON
from src.ui.sidebar import Sidebar
from src.ui.views.config import ConfigView
from src.ui.views.home import HomeView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIFA")
        self.setWindowIcon(QIcon(str(UI_ICON)))
        self.resize(800, 600)

        self._sidebar = Sidebar()

        self._pages = QStackedWidget()
        self._pages.addWidget(HomeView())
        self._pages.addWidget(ConfigView())

        self._sidebar.currentChanged.connect(self._pages.setCurrentIndex)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self._sidebar)
        layout.addWidget(self._pages)
        self.setCentralWidget(central)
