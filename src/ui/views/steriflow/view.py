from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from src.logic.steriflow.controller import build_default_controller
from src.ui.views.steriflow.config_page import SteriflowConfigPage
from src.ui.views.steriflow.data_page import SteriflowDataPage
from src.ui.views.steriflow.home_page import SteriflowHomePage
from src.ui.views.steriflow.logs_page import SteriflowLogsPage
from src.ui.views.steriflow.tab_bar import SteriflowTabBar


class SteriflowView(QWidget):
    def __init__(self):
        super().__init__()

        self._controller = build_default_controller()
        self._controller.start()

        self._tabs = SteriflowTabBar()
        self._pages = QStackedWidget()
        self._pages.addWidget(SteriflowHomePage(self._controller))
        self._pages.addWidget(SteriflowConfigPage(self._controller))
        self._pages.addWidget(SteriflowDataPage())
        self._pages.addWidget(SteriflowLogsPage(self._controller))

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)
