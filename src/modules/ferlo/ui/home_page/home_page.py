from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from src.modules.ferlo.logic.ingest.pending import MachinePending, PendingReport
from src.modules.ferlo.logic.ingest.service import BatchSummary
from src.modules.ferlo.logic.logs import FERLO_LOGS_ROOT, agent_logger
from src.modules.ferlo.messages import catalog
from src.modules.ferlo.tasks.import_runner import ImportRunner
from src.shared.assets.paths import STATUS_GREEN, STATUS_GREY, STATUS_YELLOW
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import (
    AppFolderButton,
    AppStartButton,
    AppStatusButton,
)
from src.shared.ui.components.loading_overlay import LoadingOverlay

_HEADERS = ["Máquina", "Fichero", "Filas", "Nuevas", "Duplicadas", "Ya visto"]
_COL_MACHINE = 0
_COL_FILE = 1
_COL_ROWS = 2
_COL_NEW = 3
_COL_DUPLICATE = 4
_COL_SEEN = 5


class FerloHomePage(QWidget):
    """La rutina diaria: comprobar qué ha llegado, importarlo todo de una vez y
    ver qué salió. Mismo reparto de acciones que la pantalla de inicio de
    Steriflow -check, importar, analizar- pero sobre carpetas en vez de sobre
    la red. Nada aquí se dispara solo (D4): ver `tasks/import_runner.py`.
    """

    def __init__(self, controller: FerloController):
        super().__init__()

        self._controller = controller
        self._runner = ImportRunner(controller)
        self._runner.started.connect(self._on_started)
        self._runner.finished.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)

        # Qué hacer con el resultado que devuelva la acción en curso: cada
        # acción produce un tipo distinto (PendingReport, BatchSummary) y el
        # runner es agnóstico, así que quien la lanza deja aquí quién lo pinta.
        self._on_result = None

        self._results_table = self._build_results_table()
        self._summary_label = QLabel("Pulsa Comprobar para ver qué hay pendiente de importar.")
        self._summary_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_status_machine_group())
        layout.addWidget(self._build_actions_group())
        layout.addWidget(self._build_folders_group())
        layout.addWidget(self._build_results_group())
        layout.addStretch()

        self._loading_overlay = LoadingOverlay(self)

    def _build_status_machine_group(self):
        """Un chip por máquina con lo que encontró el último check: gris sin
        comprobar, verde con ficheros nuevos, amarillo si lo que hay ya se
        importó antes. Igual que los chips de autoclave de Steriflow, salvo que
        aquí un chip no relanza nada por su cuenta -el check lee las cinco
        carpetas de una pasada y cuesta lo mismo hacerlas todas."""
        group = QGroupBox("Entradas por máquina")

        self._status_buttons: dict[str, AppStatusButton] = {}
        group_layout = QHBoxLayout(group)

        for machine in self._controller.machines:
            button = AppStatusButton(machine, STATUS_GREY)
            button.setToolTip("Sin comprobar todavía.")
            button.setCursor(Qt.CursorShape.ArrowCursor)
            self._status_buttons[machine] = button
            group_layout.addWidget(button)

        group_layout.addStretch()
        return group

    def _build_actions_group(self):
        group = QGroupBox("Acciones")

        self._check_button = AppStartButton("Comprobar")
        self._check_button.setToolTip(
            "Mira qué CSV hay en la entrada de cada máquina y cuáles ya se importaron."
        )
        self._check_button.clicked.connect(self._on_check_clicked)

        self._import_button = AppStartButton("Importar")
        self._import_button.setToolTip(
            "Funde la entrada de las cinco máquinas en sus mensuales del archivo "
            "y analiza los ciclos de los meses tocados."
        )
        self._import_button.clicked.connect(self._on_import_clicked)

        self._analyze_button = AppStartButton("Analizar")
        self._analyze_button.setToolTip(
            "Vuelve a analizar los ciclos de todos los mensuales del archivo, sin "
            "importar nada. Útil tras cambiar los umbrales en Configuración."
        )
        self._analyze_button.clicked.connect(self._on_analyze_clicked)

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(self._check_button)
        group_layout.addWidget(self._import_button)
        group_layout.addWidget(self._analyze_button)
        group_layout.addStretch()

        return group

    def _build_folders_group(self):
        group = QGroupBox("Carpetas")

        logger = agent_logger()
        settings = self._controller.settings

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(AppFolderButton("Abrir logs", FERLO_LOGS_ROOT, logger, create=True))
        group_layout.addWidget(
            AppFolderButton("Abrir entrada", settings.entrada_dir, logger, create=True)
        )
        group_layout.addWidget(
            AppFolderButton("Abrir archivo", settings.archivo_dir, logger, create=True)
        )
        group_layout.addStretch()

        return group

    def _build_results_group(self):
        group = QGroupBox("Resultado de la última acción")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._summary_label)
        group_layout.addWidget(self._results_table)
        return group

    def _build_results_table(self):
        table = QTableWidget(0, len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.horizontalHeader().setSectionResizeMode(_COL_FILE, QHeaderView.ResizeMode.Stretch)
        for column in (_COL_MACHINE, _COL_ROWS, _COL_NEW, _COL_DUPLICATE, _COL_SEEN):
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    # --- acciones ---

    def _launch(self, action, on_result, busy_text: str) -> None:
        self._busy_text = busy_text
        self._on_result = on_result
        if not self._runner.run(action):
            push(Module.FERLO, catalog.action_busy())

    def _on_check_clicked(self):
        self._launch(
            self._controller.check_pending, self._render_check, "Comprobando entradas..."
        )

    def _on_import_clicked(self):
        self._launch(
            self._controller.import_all, self._render_import, "Importando las cinco máquinas..."
        )

    def _on_analyze_clicked(self):
        if not self._controller.has_archived_months():
            push(Module.FERLO, catalog.no_archived_months())
            return
        self._launch(
            self._controller.reanalyze_all, self._render_analysis, "Reanalizando el archivo..."
        )

    def _on_started(self):
        self._set_buttons_enabled(False)
        self._loading_overlay.start(self._busy_text)

    def _on_finished(self, result: object):
        self._set_buttons_enabled(True)
        self._loading_overlay.finish()
        self._on_result(result)

    def _on_failed(self, error: object):
        self._set_buttons_enabled(True)
        self._loading_overlay.finish()
        announce(agent_logger(), catalog.action_failed(error))

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for button in (self._check_button, self._import_button, self._analyze_button):
            button.setEnabled(enabled)

    # --- pintado de resultados ---

    def _render_check(self, report: PendingReport):
        for pending in report.machines:
            self._update_status_chip(pending)

        self._results_table.setRowCount(0)
        for pending in report.machines:
            for filename in pending.new_files:
                self._append_row(pending.machine, filename, seen=False)
            for filename in pending.already_arrived:
                self._append_row(pending.machine, filename, seen=True)

        notice = catalog.check_finished(report)
        self._summary_label.setText(notice.text)
        # El check no cambia nada, pero sí es lo que decide si hoy hay algo que
        # importar: queda en el log para poder reconstruir después por qué una
        # mañana no se importó nada.
        announce(agent_logger(), notice)

    def _update_status_chip(self, pending: MachinePending) -> None:
        button = self._status_buttons.get(pending.machine)
        if button is None:
            return

        if pending.has_new:
            button.set_icon(STATUS_GREEN)
            button.setToolTip(f"{len(pending.new_files)} fichero(s) nuevo(s) por importar")
        elif pending.already_arrived:
            button.set_icon(STATUS_YELLOW)
            button.setToolTip(
                f"{len(pending.already_arrived)} fichero(s), todos importados ya"
            )
        else:
            button.set_icon(STATUS_GREY)
            button.setToolTip("Nada pendiente en la entrada")

    def _render_import(self, batch: BatchSummary):
        self._results_table.setRowCount(0)
        for summary in batch.summaries:
            for arrival in summary.arrivals:
                row = self._append_row(
                    summary.machine, arrival.filename, seen=arrival.already_seen
                )
                self._results_table.setItem(row, _COL_ROWS, self._numeric_item(arrival.rows))
                self._results_table.setItem(row, _COL_NEW, self._numeric_item(arrival.new_rows))
                self._results_table.setItem(
                    row, _COL_DUPLICATE, self._numeric_item(arrival.duplicate_rows)
                )

        # Tras importar, la entrada queda vacía (D1): los chips ya no reflejan
        # nada pendiente, y dejarlos en verde diría que queda trabajo por hacer.
        for button in self._status_buttons.values():
            button.set_icon(STATUS_GREY)
            button.setToolTip("Entrada vacía tras la importación")

        notice = catalog.import_all_finished(batch)
        self._summary_label.setText(self._import_detail(batch, notice.text))
        announce(agent_logger(), notice)

    def _import_detail(self, batch: BatchSummary, texto: str) -> str:
        restos = sum(s.leftovers_removed for s in batch.summaries)
        if restos:
            texto += f" · {restos} fichero(s) sobrante(s) retirados de las entradas"

        meses = sorted(
            {mes for s in batch.summaries for mes in s.cycles_by_month},
        )
        if meses:
            texto += " · meses tocados: " + ", ".join(f"{a:04d}-{m:02d}" for a, m in meses)
        return texto

    def _render_analysis(self, batch: BatchSummary):
        self._results_table.setRowCount(0)
        notice = catalog.analysis_finished(batch)
        self._summary_label.setText(notice.text)
        announce(agent_logger(), notice)

    def _append_row(self, machine: str, filename: str, seen: bool) -> int:
        row = self._results_table.rowCount()
        self._results_table.insertRow(row)
        self._results_table.setItem(row, _COL_MACHINE, QTableWidgetItem(machine))
        self._results_table.setItem(row, _COL_FILE, QTableWidgetItem(filename))
        self._results_table.setItem(row, _COL_SEEN, QTableWidgetItem("Sí" if seen else ""))
        return row

    @staticmethod
    def _numeric_item(value: int) -> QTableWidgetItem:
        item = QTableWidgetItem(str(value))
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item
