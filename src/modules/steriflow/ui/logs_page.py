from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.steriflow.logic.controller import BACKUP_LOG_PREFIX, SteriflowController
from src.shared.logs.files import LogTailer
from src.shared.logs.history import list_backup_logs

_POLL_INTERVAL_MS = 1000
_COL_DATE = 0
_COL_TIME = 1


class SteriflowLogsPage(QWidget):
    """Historial de ejecuciones de backup: steriflow_agent.log vive en la vista
    global de Logs del navbar, no aquí. Con varias ejecuciones al día, la tabla
    es lo que escala; un combo con decenas de entradas no."""

    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._controller = controller
        self._tailer = None
        self._current_path = None
        self._rows: list[tuple] = []  # (datetime, Path) por fila, más reciente primero

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Fecha", "Hora"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_row_selected)

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
        top_layout.addStretch()
        top_layout.addWidget(self._follow_checkbox)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self._table, 1)
        layout.addWidget(self._text_view, 2)

        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_table(select_latest=self._current_path is None)
        self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def _logs_directory(self):
        return self._controller.settings.paths.logs_root

    def _refresh_table(self, select_latest: bool):
        self._rows = list_backup_logs(self._logs_directory(), BACKUP_LOG_PREFIX)

        self._table.blockSignals(True)
        self._table.setRowCount(len(self._rows))
        for row, (moment, _path) in enumerate(self._rows):
            self._table.setItem(row, _COL_DATE, QTableWidgetItem(moment.strftime("%d/%m/%Y")))
            self._table.setItem(row, _COL_TIME, QTableWidgetItem(moment.strftime("%H:%M:%S")))
        self._table.blockSignals(False)

        if not self._rows:
            self._current_path = None
            self._tailer = None
            self._text_view.clear()
            return

        if select_latest:
            self._select_row(0)
            return

        for row, (_moment, path) in enumerate(self._rows):
            if path == self._current_path:
                self._select_row(row)
                return

        self._select_row(0)

    def _select_row(self, row: int):
        # Selección programática: no dependemos de itemSelectionChanged (no
        # dispara si la fila ya estaba seleccionada), cargamos el contenido
        # explícitamente siempre.
        self._table.blockSignals(True)
        self._table.selectRow(row)
        self._table.blockSignals(False)
        self._load_row(row)

    def _on_row_selected(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._rows):
            return

        self._follow_checkbox.setChecked(row == 0)
        self._load_row(row)

    def _load_row(self, row: int):
        path = self._rows[row][1]
        self._current_path = path
        self._tailer = LogTailer(path)
        try:
            self._text_view.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            self._text_view.setPlainText("")
        self._tailer.read_new_text()  # sincroniza el offset con lo ya mostrado
        self._scroll_to_bottom()

    def _poll(self):
        latest = list_backup_logs(self._logs_directory(), BACKUP_LOG_PREFIX)
        latest_path = latest[0][1] if latest else None

        if self._follow_checkbox.isChecked() and latest_path is not None and self._current_path != latest_path:
            self._refresh_table(select_latest=True)
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
