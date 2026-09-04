from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from src.modules.registry import MODULES
from src.shared.assets.resources import UI_ICON
from src.shared.characters.message_bar import MessageBar
from src.app.nav_bar import Navbar


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

        # Una página por módulo registrado, en el mismo orden que Navbar
        # recorre para sus botones (ver src/modules/registry.py): los dos
        # se generan de la misma lista, así que nunca pueden desincronizarse
        # por índice.
        self._pages = QStackedWidget()
        for spec in MODULES:
            self._pages.addWidget(spec.view())

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
