from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from src.shared.assets.resources import UI_ICON
from src.shared.characters.message_bar import MessageBar
from src.ui.nav_bar import Navbar
from src.ui.views.config import ConfigView
from src.ui.views.ferlo import FerloView
from src.ui.views.home import HomeView
from src.ui.views.logs import LogsView
from src.ui.views.macona import MaconaView
from src.ui.views.pasteurization import PasteurizationView
from src.ui.views.prueba_ui import PruebaUIView
from src.ui.views.steriflow import SteriflowView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIFA")
        self.setWindowIcon(QIcon(str(UI_ICON)))
        # minimun size to avoid the navbar and the pages to be too small
        self.setMinimumSize(800, 600)
        # full screen for default, but the user can resize it if they want
        self.showMaximized()

        self._navbar = Navbar()

        self._pages = QStackedWidget()
        self._pages.addWidget(HomeView())
        self._pages.addWidget(FerloView())
        self._pages.addWidget(SteriflowView())
        self._pages.addWidget(MaconaView())
        self._pages.addWidget(PasteurizationView())
        self._pages.addWidget(ConfigView())
        self._pages.addWidget(LogsView())
        self._pages.addWidget(PruebaUIView())

        self._navbar.currentChanged.connect(self._pages.setCurrentIndex)

        self._message_bar = MessageBar()

        # Tres columnas: navbar (izquierda) | páginas (centro) | message_bar
        # (derecha), igual de ancho fijo que navbar. Antes MessageBar era un
        # widget flotante sobre self._pages; ahora es una columna más, así
        # no necesita reposicionarse a mano en cada resize.
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self._navbar)
        layout.addWidget(self._pages)
        layout.addWidget(self._message_bar)
        self.setCentralWidget(central)
