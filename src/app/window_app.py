from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from src.modules.registry import MODULES
from src.shared.assets.paths import APP_ICON
from src.shared.characters import conversation
from src.shared.characters.message_bar import MessageBar
from src.shared.config.app_config import load_settings
from src.app.nav_bar import Navbar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(load_settings().name)
        self.setWindowIcon(QIcon(str(APP_ICON)))
        self.setMinimumSize(800, 600)
        self.showMaximized()    

        # Navbar
        self._navbar = Navbar() 
        self._pages = QStackedWidget()
        for spec in MODULES:
            self._pages.addWidget(spec.view())
        self._navbar.currentChanged.connect(self._pages.setCurrentIndex)

        # Conversaciones
        self._message_bar = MessageBar()    
        self._conversations = conversation.attach(self._message_bar)

        """
        layout con 3 columnas
            - left: navbar
            - center: ModulePage
            - right: message_bar
        
        """

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self._navbar)
        layout.addWidget(self._pages)
        layout.addWidget(self._message_bar)
        self.setCentralWidget(central)
