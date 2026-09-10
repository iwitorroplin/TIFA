from __future__ import annotations

from PySide6.QtCore import QDate, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
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
from src.modules.ferlo.messages import catalog
from src.modules.ferlo.logic.analysis.programs import MANUAL_PROGRAM_CODE
from src.modules.ferlo.ui.assign_program_dialog import AssignProgramDialog
from src.modules.ferlo.ui.data_presenter import (
    DEFAULT_PAGE_SIZE,
    FerloDataPresenter,
)
from src.modules.ferlo.ui.detail_dialog import FerloDetailDialog
from src.shared.messages.notice import push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppButton

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

_PAGE_SIZES = [20, 50, 100]
_FILTER_DEBOUNCE_MS = 300


class FerloDataPage(QWidget):
    def __init__(self, controller: FerloController):
        super().__init__()

        self._controller = controller
        self._presenter = FerloDataPresenter()

        self._filter_debounce = QTimer(self)
        self._filter_debounce.setSingleShot(True)
        self._filter_debounce.setInterval(_FILTER_DEBOUNCE_MS)
        self._filter_debounce.timeout.connect(self._on_filters_changed)

        self._cycles_table = self._build_cycles_table()

        group = QGroupBox("Ciclos")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._build_filters_row())
        group_layout.addWidget(self._cycles_table)
        group_layout.addWidget(self._build_actions_row())
        group_layout.addWidget(self._build_pagination_row())

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

    def _build_filters_row(self):
        self._machine_combo = QComboBox()
        self._machine_combo.addItem("Todas", userData=None)
        for machine in self._controller.machines:
            self._machine_combo.addItem(machine, userData=machine)
        self._machine_combo.currentIndexChanged.connect(self._on_filters_changed)

        self._date_from_checkbox = QCheckBox("Desde:")
        self._date_from_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_from_edit = QDateEdit(QDate.currentDate())
        self._date_from_edit.setCalendarPopup(True)
        self._date_from_edit.setEnabled(False)
        self._date_from_edit.dateChanged.connect(self._on_filters_changed)

        self._date_to_checkbox = QCheckBox("Hasta:")
        self._date_to_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_to_edit = QDateEdit(QDate.currentDate())
        self._date_to_edit.setCalendarPopup(True)
        self._date_to_edit.setEnabled(False)
        self._date_to_edit.dateChanged.connect(self._on_filters_changed)

        self._needs_review_checkbox = QCheckBox("Solo pendientes de revisión")
        self._needs_review_checkbox.toggled.connect(self._on_filters_changed)

        clear_button = AppButton("Limpiar filtros")
        clear_button.clicked.connect(self._clear_filters)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel("Máquina:"))
        row_layout.addWidget(self._machine_combo)
        row_layout.addWidget(self._date_from_checkbox)
        row_layout.addWidget(self._date_from_edit)
        row_layout.addWidget(self._date_to_checkbox)
        row_layout.addWidget(self._date_to_edit)
        row_layout.addWidget(self._needs_review_checkbox)
        row_layout.addWidget(clear_button)
        row_layout.addStretch()
        return row

    def _build_pagination_row(self):
        self._page_size_combo = QComboBox()
        for size in _PAGE_SIZES:
            self._page_size_combo.addItem(str(size), userData=size)
        self._page_size_combo.setCurrentIndex(_PAGE_SIZES.index(DEFAULT_PAGE_SIZE))
        self._page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)

        self._previous_button = AppButton("< Anterior")
        self._previous_button.clicked.connect(self._go_previous_page)

        self._next_button = AppButton("Siguiente >")
        self._next_button.clicked.connect(self._go_next_page)

        self._pagination_label = QLabel()

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel("Mostrar:"))
        row_layout.addWidget(self._page_size_combo)
        row_layout.addStretch()
        row_layout.addWidget(self._pagination_label)
        row_layout.addWidget(self._previous_button)
        row_layout.addWidget(self._next_button)
        return row

    def _on_date_filter_toggled(self):
        self._date_from_edit.setEnabled(self._date_from_checkbox.isChecked())
        self._date_to_edit.setEnabled(self._date_to_checkbox.isChecked())
        self._on_filters_changed()

    def _clear_filters(self):
        self._filter_debounce.stop()
        self._machine_combo.setCurrentIndex(0)
        self._date_from_checkbox.setChecked(False)
        self._date_to_checkbox.setChecked(False)
        self._needs_review_checkbox.setChecked(False)
        self._presenter.clear_filters()
        self._refresh()

    def _on_filters_changed(self):
        self._presenter.set_machine(self._machine_combo.currentData())
        self._presenter.set_date_range(
            self._date_from_edit.date().toPython() if self._date_from_checkbox.isChecked() else None,
            self._date_to_edit.date().toPython() if self._date_to_checkbox.isChecked() else None,
        )
        self._presenter.set_needs_review(self._needs_review_checkbox.isChecked())
        self._refresh()

    def _on_page_size_changed(self):
        self._presenter.set_page_size(self._page_size_combo.currentData())
        self._refresh()

    def _go_previous_page(self):
        if self._presenter.go_previous():
            self._refresh()

    def _go_next_page(self):
        if self._presenter.go_next():
            self._refresh()

    def _refresh(self):
        self._presenter.reload()

        table = self._cycles_table
        table.setRowCount(0)
        for cycle in self._presenter.cycles():
            row = table.rowCount()
            table.insertRow(row)
            self._set_cycle_row(row, cycle)

        self._update_pagination_controls()

    def _update_pagination_controls(self):
        self._pagination_label.setText(self._presenter.pagination_label())
        self._previous_button.setEnabled(self._presenter.can_go_previous())
        self._next_button.setEnabled(self._presenter.can_go_next())

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
