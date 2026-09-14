from __future__ import annotations

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
from src.modules.ferlo.ui.data_page.data_view_model import FerloDataViewModel
from src.modules.ferlo.ui.data_page.detail_dialog import FerloDetailDialog
from src.shared.messages.notice import push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppButton
from src.shared.ui.components.pagination_row import PaginationRow
from src.shared.ui.review_highlight import paint_review_row

from src.modules.ferlo.ui.data_page.filters_row import FiltersRow

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


class FerloDataPage(QWidget):
    def __init__(self, controller: FerloController):
        super().__init__()

        self._controller = controller
        self._view_model = FerloDataViewModel()

        self._cycles_table = self._build_cycles_table()
        self._filters_row = FiltersRow(controller, self._view_model, self._refresh)
        self._pagination_row = PaginationRow(self._view_model, self._refresh)

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
        return self._view_model.items_at(filas)

    def _refresh(self):
        self._filters_row.apply_to_view_model()
        self._view_model.reload()

        table = self._cycles_table
        table.setRowCount(0)
        for cycle in self._view_model.items():
            row = table.rowCount()
            table.insertRow(row)
            self._set_cycle_row(row, cycle)

        self._pagination_row.repaint()

    def _set_cycle_row(self, row, cycle):
        table = self._cycles_table
        for col, text in enumerate(self._view_model.row_cells(cycle)):
            table.setItem(row, col, QTableWidgetItem(text))

        if cycle.needs_review:
            if cycle.review_notes:
                table.item(row, _COL_VERDICT).setToolTip(cycle.review_notes)
            paint_review_row(table, row)

    def _on_row_double_clicked(self, row, column):
        cycle = self._view_model.item_at(row)
        if cycle is None:
            return
        dialog = FerloDetailDialog(self._controller, cycle.id, parent=self)
        dialog.exec()
        self._refresh()  # el dialogo puede haber cambiado veredicto/programa
