from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
)

from src.modules.steriflow.logic.settings_editor import SettingsIssue
from src.modules.steriflow.messages import catalog
from src.shared.messages.notice import push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppAddButton, AppDeleteButton, AppModifyButton


class SchedulesDialog(QDialog):
    """Modal "Horarios": tabla de horas de ejecución + alta/edición/baja.

    Edita el borrador del view model directamente fila a fila (igual que el
    resto de grupos de config_page), no acumula un estado propio: cerrar el
    diálogo con la X o con "Cerrar" deja los cambios ya hechos, el guardado
    real sigue siendo cosa del botón "Guardar cambios" de la página."""

    def __init__(self, view_model, on_change, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Horarios")
        self._view_model = view_model
        self._on_change = on_change

        self._table = QTableWidget(0, 1)
        self._table.setHorizontalHeaderLabels(["Hora"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setMinimumWidth(240)

        add_button = AppAddButton("Añadir")
        add_button.clicked.connect(self._add_row)

        remove_button = AppDeleteButton("Eliminar")
        remove_button.clicked.connect(self._remove_selected_row)

        edit_button = AppModifyButton("Editar")
        edit_button.clicked.connect(self._edit_selected_row)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(remove_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addStretch()

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        close_box.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(buttons_layout)
        layout.addWidget(close_box)

        self._repaint()

    def _add_row(self):
        dialog = _ScheduleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._view_model.add_hour(dialog.value().toPython())
            self._on_change()
            self._repaint()

    def _remove_selected_row(self):
        row = self._table.currentRow()
        if row < 0:
            return

        if not self._view_model.can_remove_hour():
            push(Module.STERIFLOW, catalog.settings_issue(SettingsIssue.AT_LEAST_ONE_SCHEDULE))
            return

        self._view_model.remove_hour(row)
        self._on_change()
        self._repaint()

    def _edit_selected_row(self):
        row = self._table.currentRow()
        if row < 0:
            return

        hour = self._view_model.hours()[row]
        dialog = _ScheduleDialog(self, time=QTime(hour.hour, hour.minute))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._view_model.update_hour(row, dialog.value().toPython())
            self._on_change()
            self._repaint()

    def _repaint(self):
        table = self._table
        current_row = table.currentRow()

        table.setRowCount(0)
        for hour in self._view_model.hours():
            row = table.rowCount()
            table.insertRow(row)
            self._set_row(row, QTime(hour.hour, hour.minute))

        if 0 <= current_row < table.rowCount():
            table.selectRow(current_row)

    def _set_row(self, row, qtime):
        time_item = QTableWidgetItem(qtime.toString("HH:mm"))
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 0, time_item)


class _ScheduleDialog(QDialog):
    def __init__(self, parent=None, time=None):
        super().__init__(parent)
        self.setWindowTitle("Horario")

        self._time_edit = QTimeEdit(time or QTime(0, 0))
        self._time_edit.setDisplayFormat("HH:mm")

        form_layout = QFormLayout()
        form_layout.addRow("Hora:", self._time_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def value(self):
        return self._time_edit.time()
