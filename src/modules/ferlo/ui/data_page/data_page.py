from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.controller import FerloController
from src.modules.ferlo.messages import catalog
from src.modules.ferlo.logic.analysis.programs import MANUAL_PROGRAM_CODE
from src.modules.ferlo.ui.data_page.assign_program_dialog import AssignProgramDialog
from src.modules.ferlo.ui.data_page.data_presenter import FerloDataPresenter
from src.modules.ferlo.ui.data_page.detail_dialog import FerloDetailDialog
from src.shared.messages.notice import push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppButton

from src.modules.ferlo.ui.data_page.filters_row import FiltersRow
from src.modules.ferlo.ui.data_page.pagination_row import PaginationRow

_COL_MACHINE = 0
_COL_STARTED_AT = 1
_COL_PROGRAM = 2
_COL_STERILIZATION_DURATION = 3
_COL_CYCLE_DURATION = 4
_COL_MEAN = 5
_COL_MEAN_STABLE = 6
_COL_STATUS = 7
_COL_VERDICT = 8

_HEADERS = [
    "Máquina",
    "Fecha inicio",
    "Programa",
    "Duración esterilización (min)",
    "Duración ciclo (min)",
    "T media (°C)",
    "T media estable (°C)",
    "Estado",
    "Revisión",
]

# Mismo criterio visual que Steriflow: fondo y letra fijados los dos, para
# que se vea igual con tema claro u oscuro.
_REVIEW_BACKGROUND = QColor(255, 244, 200)
_REVIEW_FOREGROUND = QColor(90, 60, 0)


class FerloDataPage(QWidget):
    def __init__(self, controller: FerloController):
        super().__init__()

        self._controller = controller
        self._presenter = FerloDataPresenter()

        self._cycles_table = self._build_cycles_table()
        self._filters_row = FiltersRow(controller, self._presenter, self._refresh)
        self._pagination_row = PaginationRow(
            self._presenter, self._on_page_size_changed, self._go_previous_page, self._go_next_page
        )

        group = QGroupBox("Ciclos")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._filters_row)
        group_layout.addWidget(self._cycles_table)
        group_layout.addWidget(self._build_actions_row())
        group_layout.addWidget(self._pagination_row)

        layout = QVBoxLayout(self)
        layout.addWidget(group)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _build_cycles_table(self):
        table = QTableWidget(0, len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(_COL_PROGRAM, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Selección múltiple (igual que la tabla de Steriflow): es lo que
        # permite asignar un programa a varios ciclos de una vez, que es como
        # llegan -una tanda entera del mismo producto-.
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.cellDoubleClicked.connect(self._on_row_double_clicked)
        return table

    def _build_actions_row(self):
        assign_button = AppButton("Asignar a la selección...")
        assign_button.setToolTip(
            "Abre el selector de consigna y reevalúa con ella todos los ciclos "
            "seleccionados."
        )
        assign_button.clicked.connect(self._on_assign_selection_clicked)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(assign_button)
        row_layout.addStretch()
        return row

    def _on_assign_selection_clicked(self):
        seleccion = self._selected_cycles()
        if not seleccion:
            push(Module.FERLO, catalog.no_cycles_selected_to_assign())
            return

        # El diálogo hace de confirmación: reasignar reescribe el veredicto
        # calculado de cada ciclo, y con selección múltiple un clic de más
        # puede tocar una pantalla entera. Los programas se leen aquí y no en
        # el arranque porque se editan en otra pestaña.
        dialogo = AssignProgramDialog(
            self._controller.list_programs(include_inactive=True), len(seleccion), self
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        manual = dialogo.manual_setpoint()
        program_code = MANUAL_PROGRAM_CODE if manual else dialogo.program_code()

        reasignados = self._controller.reassign_programs(
            [(cycle.machine, cycle.started_at) for cycle in seleccion], program_code, manual
        )
        if manual is not None:
            push(Module.FERLO, catalog.manual_setpoints_assigned(
                reasignados, len(seleccion),
                manual.target_temperature_c, manual.target_time_min,
            ))
        else:
            push(Module.FERLO, catalog.programs_assigned(
                reasignados, len(seleccion), program_code
            ))
        self._refresh()

    def _selected_cycles(self):
        filas = sorted({index.row() for index in self._cycles_table.selectionModel().selectedRows()})
        return self._presenter.cycles_at(filas)

    def _on_page_size_changed(self, size):
        self._presenter.set_page_size(size)
        self._refresh()

    def _go_previous_page(self):
        if self._presenter.go_previous():
            self._refresh()

    def _go_next_page(self):
        if self._presenter.go_next():
            self._refresh()

    def _refresh(self):
        self._filters_row.apply_to_presenter()
        self._presenter.reload()

        table = self._cycles_table
        table.setRowCount(0)
        for cycle in self._presenter.cycles():
            row = table.rowCount()
            table.insertRow(row)
            self._set_cycle_row(row, cycle)

        self._pagination_row.repaint()

    def _set_cycle_row(self, row, cycle):
        table = self._cycles_table
        for col, text in enumerate(self._presenter.row_cells(cycle)):
            table.setItem(row, col, QTableWidgetItem(text))

        if cycle.needs_review:
            if cycle.review_notes:
                table.item(row, _COL_VERDICT).setToolTip(cycle.review_notes)
            for col in range(table.columnCount()):
                item = table.item(row, col)
                item.setBackground(_REVIEW_BACKGROUND)
                item.setForeground(_REVIEW_FOREGROUND)

    def _on_row_double_clicked(self, row, column):
        cycle = self._presenter.cycle_at(row)
        if cycle is None:
            return
        dialog = FerloDetailDialog(self._controller, cycle.id, parent=self)
        dialog.exec()
        self._refresh()  # el dialogo puede haber cambiado veredicto/programa
