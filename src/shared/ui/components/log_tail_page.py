from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from src.shared.logs.files import LogTailer

_POLL_INTERVAL_MS = 1000


class LogTailPage(QWidget):
    """Muestra en vivo, tipo terminal, un único archivo de log que va creciendo."""

    def __init__(self, path: Path):
        super().__init__()

        self._path = path
        self._tailer = LogTailer(path)

        self._text_view = QPlainTextEdit()
        self._text_view.setReadOnly(True)
        self._text_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text_view.setFont(QFont("Consolas", 10))
        self._text_view.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )

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
            self._text_view.setPlainText(self._path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            self._text_view.setPlainText("")
        self._tailer.read_new_text()  # sincroniza el offset con lo ya mostrado
        self._scroll_to_bottom()

    def _poll(self):
        new_text = self._tailer.read_new_text()
        if new_text:
            self._text_view.appendPlainText(new_text.rstrip("\n"))
            self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        scrollbar = self._text_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
