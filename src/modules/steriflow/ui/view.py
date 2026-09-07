from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from src.modules.steriflow.logic.controller import build_default_controller
from src.modules.steriflow.ui.config_page import SteriflowConfigPage
from src.modules.steriflow.ui.data_page import SteriflowDataPage
from src.modules.steriflow.ui.home_page import SteriflowHomePage
from src.modules.steriflow.ui.logs_page import SteriflowLogsPage
from src.modules.steriflow.ui.tab_bar import SteriflowTabBar


class SteriflowView(QWidget):
    def __init__(self):
        super().__init__()

        self._controller = build_default_controller()
        # Arranca el scheduler solo si el usuario no lo había parado a mano la
        # última vez (ver SteriflowController.set_auto_enabled): si no,
        # apagarlo desde la home page duraría hasta el siguiente reinicio.
        if self._controller.auto_enabled:
            self._controller.start()

        self._tabs = SteriflowTabBar()
        self._pages = QStackedWidget()
        self._pages.addWidget(SteriflowHomePage(self._controller))
        self._pages.addWidget(SteriflowConfigPage(self._controller))
        self._pages.addWidget(SteriflowDataPage())
        self._pages.addWidget(SteriflowLogsPage())

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)
