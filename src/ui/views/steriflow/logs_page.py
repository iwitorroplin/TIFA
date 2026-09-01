from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.logic.steriflow.controller import SteriflowController
from src.logic.steriflow.logs.files import LogTailer, list_log_files

_POLL_INTERVAL_MS = 1000


class SteriflowLogsPage(QWidget):
    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._controller = controller
        self._tailer = None

        self._file_combo = QComboBox()
        self._file_combo.currentIndexChanged.connect(self._on_file_selected)

        self._follow_checkbox = QCheckBox("Seguir")
        self._follow_checkbox.setChecked(True)

        self._text_view = QPlainTextEdit()
        self._text_view.setReadOnly(True)
        self._text_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text_view.setFont(QFont("Consolas", 10))
        self._text_view.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._file_combo, 1)
        top_layout.addWidget(self._follow_checkbox)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self._text_view)

        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_file_list(select_latest=self._file_combo.currentIndex() < 0)
        self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def _logs_directory(self):
        return self._controller.settings.paths.logs_root

    def _refresh_file_list(self, select_latest: bool):
        files = list_log_files(self._logs_directory())
        current_path = self._file_combo.currentData()

        self._file_combo.blockSignals(True)
        self._file_combo.clear()
        for file in files:
            self._file_combo.addItem(file.name, file)
        self._file_combo.blockSignals(False)

        if not files:
            self._tailer = None
            self._text_view.clear()
            return

        if select_latest:
            self._select_file(files[0])
        elif current_path in files:
            self._file_combo.setCurrentIndex(files.index(current_path))
        else:
            self._select_file(files[0])

    def _select_file(self, path):
        index = self._file_combo.findData(path)
        if index >= 0:
            self._file_combo.setCurrentIndex(index)
        else:
            self._load_file(path)

    def _on_file_selected(self, index):
        path = self._file_combo.itemData(index)
        if path is None:
            return

        files = list_log_files(self._logs_directory())
        is_latest = bool(files) and path == files[0]
        self._follow_checkbox.setChecked(is_latest)
        self._load_file(path)

    def _load_file(self, path):
        self._tailer = LogTailer(path)
        try:
            self._text_view.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            self._text_view.setPlainText("")
        self._tailer.read_new_text()  # sincroniza el offset con lo ya mostrado
        self._scroll_to_bottom()

    def _poll(self):
        files = list_log_files(self._logs_directory())
        if self._follow_checkbox.isChecked() and files and self._file_combo.currentData() != files[0]:
            self._refresh_file_list(select_latest=True)
            return

        if self._tailer is None:
            return

        new_text = self._tailer.read_new_text()
        if new_text:
            self._text_view.appendPlainText(new_text.rstrip("\n"))
            self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        scrollbar = self._text_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
