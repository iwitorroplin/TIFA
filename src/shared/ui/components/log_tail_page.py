from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.shared.logs.files import LogTailer
from src.shared.ui.components.log_text_view import LogTextView

_POLL_INTERVAL_MS = 1000


class LogTailPage(QWidget):
    """Muestra en vivo, tipo terminal, un único archivo de log que va creciendo."""

    def __init__(self, path: Path):
        super().__init__()

        self._path = path
        self._tailer = LogTailer(path)

        self._text_view = LogTextView()

        layout = QVBoxLayout(self)
        layout.addWidget(self._text_view)

        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_current_content()
        self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def _load_current_content(self):
        try:
            self._text_view.set_log_text(self._path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            self._text_view.set_log_text("")
        self._tailer.read_new_text()  # sincroniza el offset con lo ya mostrado
        self._text_view.scroll_to_bottom()

    def _poll(self):
        new_text = self._tailer.read_new_text()
        if new_text:
            self._text_view.append_log_text(new_text)
            self._text_view.scroll_to_bottom()
