from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from src.modules.ferlo.logic.controller import build_default_controller
from src.modules.ferlo.ui.config_page import FerloConfigPage
from src.modules.ferlo.ui.data_page import FerloDataPage
from src.modules.ferlo.ui.import_page import FerloImportPage
from src.modules.ferlo.ui.tab_bar import FerloTabBar


class FerloView(QWidget):
    def __init__(self):
        super().__init__()

        self._controller = build_default_controller()

        self._tabs = FerloTabBar()
        self._pages = QStackedWidget()
        self._pages.addWidget(FerloImportPage(self._controller))
        self._pages.addWidget(FerloDataPage(self._controller))
        self._pages.addWidget(FerloConfigPage(self._controller))

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)
