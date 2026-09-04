from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from src.logic.steriflow.config import load_settings
from src.logic.steriflow.controller import AGENT_LOG_FILENAME
from src.shared.ui.components.log_tail_page import LogTailPage
from src.ui.views.logs.tab_bar import LogsTabBar


class LogsView(QWidget):
    """Actividad de cada módulo en un solo sitio. Los backups de Steriflow (que
    corren varias veces al día) no están aquí: tienen su propia tabla dentro
    del módulo, en Steriflow > Logs."""

    def __init__(self):
        super().__init__()

        self._tabs = LogsTabBar()
        self._pages = QStackedWidget()
        self._pages.addWidget(self._placeholder_page("Ferlo · Aún no hay actividad registrada"))
        self._pages.addWidget(self._steriflow_agent_page())
        self._pages.addWidget(self._placeholder_page("Macona · Aún no hay actividad registrada"))
        self._pages.addWidget(self._placeholder_page("Pasteurización · Aún no hay actividad registrada"))

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)

    def _steriflow_agent_page(self):
        logs_root = load_settings().paths.logs_root
        return LogTailPage(logs_root / AGENT_LOG_FILENAME)

    def _placeholder_page(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
