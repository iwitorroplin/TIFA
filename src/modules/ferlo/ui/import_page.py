from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.controller import FerloController
from src.modules.ferlo.logic.ingest.service import ImportSummary
from src.modules.ferlo.logic.logs import FERLO_LOGS_ROOT, agent_logger
from src.modules.ferlo.messages import catalog
from src.modules.ferlo.tasks.import_runner import ImportRunner
from src.shared.messages.notice import push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppFolderButton, AppStartButton
from src.shared.ui.components.loading_overlay import LoadingOverlay

_HEADERS = ["Fichero", "Filas", "Nuevas", "Ya visto"]
_COL_ROWS = 1
_COL_NEW = 2
_COL_SEEN = 3


class FerloImportPage(QWidget):
    """La rutina diaria de la Fase 4: elegir máquina, pulsar Importar (D4) y
    ver qué llegó. Nada aquí se dispara solo -ver el docstring de
    `tasks/import_runner.py`."""

    def __init__(self, controller: FerloController):
        super().__init__()

        self._controller = controller
        self._runner = ImportRunner(controller)
        self._runner.started.connect(self._on_started)
        self._runner.finished.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)

        self._machine_combo = QComboBox()
        self._machine_combo.addItems(list(controller.machines))
        self._machine_combo.currentTextChanged.connect(self._rebuild_folder_buttons)

        self._import_button = AppStartButton("Importar")
        self._import_button.setToolTip(
            "Funde lo que haya en la carpeta de entrada de esta máquina en su "
            "mensual del archivo y reanaliza los meses tocados."
        )
        self._import_button.clicked.connect(self._on_import_clicked)

        self._folders_row = QWidget()
        self._folders_layout = QHBoxLayout(self._folders_row)
        self._folders_layout.setContentsMargins(0, 0, 0, 0)

        self._results_table = self._build_results_table()
        self._summary_label = QLabel("Elige una máquina e importa para ver el resultado aquí.")
        self._summary_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_import_group())
        layout.addWidget(self._build_folders_group())
        layout.addWidget(self._build_results_group())
        layout.addStretch()

        self._loading_overlay = LoadingOverlay(self)
        self._rebuild_folder_buttons(self._machine_combo.currentText())

    def _build_import_group(self):
        group = QGroupBox("Importar")

        row = QHBoxLayout()
        row.addWidget(QLabel("Máquina:"))
        row.addWidget(self._machine_combo)
        row.addWidget(self._import_button)
        row.addStretch()

        group_layout = QVBoxLayout(group)
        group_layout.addLayout(row)
        return group

    def _build_folders_group(self):
        group = QGroupBox("Carpetas")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._folders_row)
        return group

    def _build_results_group(self):
        group = QGroupBox("Resultado de la última importación")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._summary_label)
        group_layout.addWidget(self._results_table)
        return group

    def _build_results_table(self):
        table = QTableWidget(0, len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            _COL_ROWS, QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            _COL_NEW, QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            _COL_SEEN, QHeaderView.ResizeMode.ResizeToContents
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _rebuild_folder_buttons(self, machine: str):
        # AppFolderButton fija su carpeta al construirse: al cambiar de
        # máquina se reconstruyen en vez de mutarlas (igual que
        # SteriflowConfigPage repinta tablas enteras en vez de tocar celdas).
        while self._folders_layout.count():
            item = self._folders_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        logger = agent_logger()
        entrada_dir = self._controller.settings.entrada_dir / machine
        archivo_dir = self._controller.settings.archivo_dir / machine

        open_logs = AppFolderButton("Abrir logs", FERLO_LOGS_ROOT, logger, create=True)
        open_entrada = AppFolderButton(f"Abrir entrada/{machine}", entrada_dir, logger, create=True)
        open_archivo = AppFolderButton(f"Abrir archivo/{machine}", archivo_dir, logger, create=True)

        self._folders_layout.addWidget(open_logs)
        self._folders_layout.addWidget(open_entrada)
        self._folders_layout.addWidget(open_archivo)
        self._folders_layout.addStretch()

    def _on_import_clicked(self):
        machine = self._machine_combo.currentText()
        if not self._runner.run(machine):
            push(Module.FERLO, catalog.import_busy())

    def _on_started(self):
        self._import_button.setEnabled(False)
        self._loading_overlay.start(f"Importando {self._machine_combo.currentText()}...")

    def _on_finished(self, machine: str, summary: ImportSummary):
        self._import_button.setEnabled(True)
        self._loading_overlay.finish()
        self._render_summary(machine, summary)
        # import_finished() ya queda en el log del módulo (ver
        # tasks/import_runner.py); esto es solo lo que se ve en pantalla.
        push(Module.FERLO, catalog.import_finished(machine, summary))

    def _on_failed(self, machine: str, error: object):
        self._import_button.setEnabled(True)
        self._loading_overlay.finish()
        push(Module.FERLO, catalog.import_failed(machine, error))

    def _render_summary(self, machine: str, summary: ImportSummary):
        self._results_table.setRowCount(0)
        for arrival in summary.arrivals:
            row = self._results_table.rowCount()
            self._results_table.insertRow(row)
            self._results_table.setItem(row, 0, QTableWidgetItem(arrival.filename))
            self._results_table.setItem(row, _COL_ROWS, self._numeric_item(arrival.rows))
            self._results_table.setItem(row, _COL_NEW, self._numeric_item(arrival.new_rows))
            self._results_table.setItem(
                row, _COL_SEEN, QTableWidgetItem("Sí" if arrival.already_seen else "")
            )

        if not summary.arrivals:
            self._summary_label.setText(f"{machine}: nada pendiente en la carpeta de entrada.")
            return

        meses = ", ".join(
            f"{anio:04d}-{mes:02d} ({len(ciclos)} ciclo(s))"
            for (anio, mes), ciclos in sorted(summary.cycles_by_month.items())
        )
        self._summary_label.setText(
            f"{machine}: {summary.total_new_rows} fila(s) nueva(s) · "
            f"{summary.total_cycles} ciclo(s) analizado(s)"
            + (f" · meses tocados: {meses}" if meses else "")
        )

    @staticmethod
    def _numeric_item(value: int) -> QTableWidgetItem:
        item = QTableWidgetItem(str(value))
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item
