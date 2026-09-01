from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from src.ui.assets import UI_ICON
from src.ui.navbar import Navbar
from src.ui.views.config import ConfigView
from src.ui.views.ferlo import FerloView
from src.ui.views.home import HomeView
from src.ui.views.macona import MaconaView
from src.ui.views.pasteurization import PasteurizationView
from src.ui.views.steriflow import SteriflowView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIFA")
        self.setWindowIcon(QIcon(str(UI_ICON)))
        self.resize(800, 600)

        self._navbar = Navbar()

        self._pages = QStackedWidget()
        self._pages.addWidget(HomeView())
        self._pages.addWidget(FerloView())
        self._pages.addWidget(SteriflowView())
        self._pages.addWidget(MaconaView())
        self._pages.addWidget(PasteurizationView())
        self._pages.addWidget(ConfigView())

        self._navbar.currentChanged.connect(self._pages.setCurrentIndex)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self._navbar)
        layout.addWidget(self._pages)
        self.setCentralWidget(central)
