from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from src.modules.logs.ui.tab_bar import LogsTabBar
from src.shared.ui.components.log_tail_page import LogTailPage


class LogsView(QWidget):
    """Actividad de cada módulo en un solo sitio. Los backups de Steriflow (que
    corren varias veces al día) no están aquí: tienen su propia tabla dentro
    del módulo, en Steriflow > Logs.

    Recibe qué módulos mostrar desde el registro (`src/modules/registry.py`),
    como pares (etiqueta, log_path); `log_path` es None para un módulo que
    todavía no tiene log real. Así esta vista no necesita importar Steriflow
    -ni ningún otro módulo- por su nombre.
    """

    def __init__(self, log_sources: Sequence[tuple[str, Callable[[], Path] | None]]):
        super().__init__()

        self._tabs = LogsTabBar([label for label, _ in log_sources])
        self._pages = QStackedWidget()
        for label, log_path in log_sources:
            if log_path is not None:
                self._pages.addWidget(LogTailPage(log_path()))
            else:
                self._pages.addWidget(
                    self._placeholder_page(f"{label} · Aún no hay actividad registrada")
                )

        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._pages)

    def _placeholder_page(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
