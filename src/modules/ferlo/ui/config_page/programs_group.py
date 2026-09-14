from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.analysis.models import SterilizationProgram
from src.modules.ferlo.logic.logs import agent_logger
from src.modules.ferlo.messages import catalog
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppAddButton, AppModifyButton

_COL_CODE = 0
_COL_NAME = 1
_COL_FORMAT = 2
_COL_TEMP = 3
_COL_TIME = 4
_COL_ACTIVE = 5


class ProgramsGroup(QGroupBox):
    """Grupo "Programas de consigna": sin Excel de origen que portar (ver
    `logic/analysis/programs.py`), se gestiona a mano. A diferencia de los
    demás grupos de esta página, escribe directo en el controller -no hay
    borrador que descartar, el alta/baja de un programa es inmediata."""

    def __init__(self, controller, parent=None):
        super().__init__("Programas de consigna", parent)
        self._controller = controller

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Código", "Nombre", "Formato", "Temperatura (°C)", "Tiempo (min)", "Activo"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_NAME, QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_button = AppAddButton("Añadir")
        add_button.clicked.connect(self._on_add_program)
        modify_button = AppModifyButton("Modificar")
        modify_button.clicked.connect(self._on_modify_program)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(add_button)
        buttons_row.addWidget(modify_button)
        buttons_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(buttons_row)

    def showEvent(self, event):
        super().showEvent(event)
        self.repaint_table()

    def repaint_table(self):
        table = self._table
        current_row = table.currentRow()

        programas = self._controller.list_programs(include_inactive=True)
        table.setRowCount(0)
        for programa in programas:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, _COL_CODE, QTableWidgetItem(programa.display_code))
            table.setItem(row, _COL_NAME, QTableWidgetItem(programa.name))
            table.setItem(row, _COL_FORMAT, QTableWidgetItem(programa.format))
            table.setItem(row, _COL_TEMP, QTableWidgetItem(f"{programa.target_temperature_c:.1f}"))
            table.setItem(row, _COL_TIME, QTableWidgetItem(f"{programa.target_time_min:.1f}"))
            table.setCellWidget(row, _COL_ACTIVE, self._build_active_checkbox(programa))

        if 0 <= current_row < table.rowCount():
            table.selectRow(current_row)

    def _build_active_checkbox(self, programa: SterilizationProgram) -> QWidget:
        checkbox = QCheckBox()
        checkbox.setChecked(programa.is_active)
        checkbox.toggled.connect(
            lambda checked, codigo=programa.code: self._on_active_toggled(codigo, checked)
        )

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(checkbox)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return container

    def _on_active_toggled(self, codigo: int, activo: bool):
        self._controller.set_program_active(codigo, activo)

    def _on_add_program(self):
        dialog = _ProgramDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            programa = dialog.value()
            if programa is None:
                push(Module.FERLO, catalog.program_code_required())
                return
            self._controller.upsert_program(programa)
            self.repaint_table()
            announce(agent_logger(), catalog.program_saved(programa.code))

    def _on_modify_program(self):
        row = self._table.currentRow()
        if row < 0:
            return
        codigo = int(self._table.item(row, _COL_CODE).text())
        programa = next(
            (p for p in self._controller.list_programs(include_inactive=True) if p.code == codigo),
            None,
        )
        if programa is None:
            return

        dialog = _ProgramDialog(self, programa=programa)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            editado = dialog.value()
            if editado is None:
                push(Module.FERLO, catalog.program_code_required())
                return
            self._controller.upsert_program(editado)
            self.repaint_table()
            announce(agent_logger(), catalog.program_saved(editado.code))


class _ProgramDialog(QDialog):
    def __init__(self, parent=None, programa: SterilizationProgram | None = None):
        super().__init__(parent)
        self.setWindowTitle("Programa de consigna")

        self._code_spin = QSpinBox()
        self._code_spin.setRange(1, 999)
        # En edición el código es la clave del programa: no se cambia.
        self._code_spin.setEnabled(programa is None)

        self._name_edit = QLineEdit()

        # Texto libre y no un número: el formato se nombra en planta con
        # fracción y unidad juntas ("1/2 kg", "1I8", "3 kg").
        self._format_edit = QLineEdit()
        self._format_edit.setPlaceholderText("1/2 kg")

        # Las unidades van en la etiqueta, no dentro del campo: repetirlas como
        # sufijo del propio input las duplicaba en pantalla y estorbaba al
        # teclear el número.
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 150.0)
        self._temp_spin.setDecimals(1)

        self._time_spin = QDoubleSpinBox()
        self._time_spin.setRange(0.0, 600.0)
        self._time_spin.setDecimals(1)

        self._active_checkbox = QCheckBox("Activo")
        self._active_checkbox.setChecked(True)

        if programa is not None:
            self._code_spin.setValue(programa.code)
            self._name_edit.setText(programa.name)
            self._format_edit.setText(programa.format)
            self._temp_spin.setValue(programa.target_temperature_c)
            self._time_spin.setValue(programa.target_time_min)
            self._active_checkbox.setChecked(programa.is_active)

        form = QFormLayout()
        form.addRow("Código:", self._code_spin)
        form.addRow("Nombre:", self._name_edit)
        form.addRow("Formato:", self._format_edit)
        form.addRow("Temperatura de consigna (°C):", self._temp_spin)
        form.addRow("Tiempo de consigna (min):", self._time_spin)
        form.addRow(self._active_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def value(self) -> SterilizationProgram | None:
        if self._code_spin.value() <= 0:
            return None
        return SterilizationProgram(
            code=self._code_spin.value(),
            name=self._name_edit.text().strip(),
            format=self._format_edit.text().strip(),
            target_temperature_c=self._temp_spin.value(),
            target_time_min=self._time_spin.value(),
            is_active=self._active_checkbox.isChecked(),
        )
