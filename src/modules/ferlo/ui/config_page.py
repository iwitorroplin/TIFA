"""Pestaña de Configuración de Ferlo (Fase 4, D7): a diferencia de
`src/modules/steriflow/ui/config_page.py` -formulario escrito a mano-, aquí
cada sección y cada campo salen de `SETTINGS_SCHEMA`
(`logic/config.py`), así que añadir un umbral nuevo no toca este fichero.

Las rutas de entrada/archivo (D1) no están en el esquema de campos -son
carpetas, no números con rango- y se editan aparte, igual que Steriflow edita
sus rutas con un `QLineEdit` + "Seleccionar...".

La tabla de programas de consigna vive aquí también: no hay Excel de origen
que portar (ver `logic/analysis/programs.py`), así que se gestiona a mano.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.config import SETTINGS_SCHEMA, Settings, save_settings
from src.modules.ferlo.logic.controller import FerloController
from src.modules.ferlo.logic.analysis.models import SterilizationProgram
from src.modules.ferlo.logic.logs import agent_logger
from src.modules.ferlo.messages import catalog
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.shared.paths import PROJECT_ROOT
from src.shared.ui.components.app_button import AppAddButton, AppButton, AppSaveButton
from src.shared.ui.components.diagram_viewer_dialog import DiagramViewerDialog

_SECTIONS_PER_ROW = 3

_COL_CODE = 0
_COL_NAME = 1
_COL_TEMP = 2
_COL_TIME = 3
_COL_ACTIVE = 4


class FerloConfigPage(QWidget):
    def __init__(self, controller: FerloController):
        super().__init__()

        self._controller = controller
        self._draft = controller.settings.as_dict()
        self._spinboxes: dict[tuple[str, str], QWidget] = {}
        self._dirty = False
        self._diagram_dialog: DiagramViewerDialog | None = None

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_top_bar())
        layout.addWidget(self._build_paths_group())
        layout.addLayout(self._build_sections_grid())
        layout.addWidget(self._build_programs_group())
        layout.addStretch()
        layout.addLayout(self._build_save_bar())

    def showEvent(self, event):
        super().showEvent(event)
        self._repaint_programs_table()

    # --- barra superior: ventana con el diagrama que explica las variables ---

    def _build_top_bar(self):
        diagram_button = AppButton("Ver diagrama de variables")
        diagram_button.clicked.connect(self._on_show_diagram)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(diagram_button)
        return row

    def _on_show_diagram(self):
        if self._diagram_dialog is None:
            self._diagram_dialog = DiagramViewerDialog(self)
        self._diagram_dialog.show()
        self._diagram_dialog.raise_()
        self._diagram_dialog.activateWindow()

    # --- rutas (D1): no forman parte del esquema de campos ---

    def _build_paths_group(self):
        group = QGroupBox("Carpetas")

        self._entrada_edit = QLineEdit(self._draft["paths"]["entrada"])
        self._entrada_edit.editingFinished.connect(
            lambda: self._on_path_edited("entrada", self._entrada_edit)
        )
        self._archivo_edit = QLineEdit(self._draft["paths"]["archivo"])
        self._archivo_edit.editingFinished.connect(
            lambda: self._on_path_edited("archivo", self._archivo_edit)
        )

        form = QFormLayout(group)
        form.addRow("Entrada (buzón transitorio):", self._path_row(self._entrada_edit))
        form.addRow("Archivo (mensual que mantiene TIFA):", self._path_row(self._archivo_edit))
        return group

    def _path_row(self, line_edit: QLineEdit):
        row = QWidget()
        browse_button = AppButton("Seleccionar...")
        browse_button.clicked.connect(lambda: self._browse_path(line_edit))

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_button)
        return row

    def _browse_path(self, line_edit: QLineEdit):
        base = str(PROJECT_ROOT / line_edit.text()) if line_edit.text() else str(PROJECT_ROOT)
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", base)
        if path:
            line_edit.setText(path)
            line_edit.editingFinished.emit()

    def _on_path_edited(self, key: str, line_edit: QLineEdit):
        self._draft["paths"][key] = line_edit.text().strip()
        self._mark_dirty()

    # --- secciones generadas desde SETTINGS_SCHEMA, en una rejilla horizontal
    # (varios grupos por fila) en vez de una sola columna: con tantas
    # secciones, apilarlas todas verticalmente desperdiciaba ancho de página ---

    def _build_sections_grid(self):
        grid = QGridLayout()
        for col in range(_SECTIONS_PER_ROW):
            grid.setColumnStretch(col, 1)
        for index, section in enumerate(SETTINGS_SCHEMA):
            row, col = divmod(index, _SECTIONS_PER_ROW)
            group = self._build_section_group(section)
            group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            grid.addWidget(group, row, col, alignment=Qt.AlignmentFlag.AlignTop)
        return grid

    def _build_section_group(self, section):
        group = QGroupBox(section.label)
        form = QFormLayout(group)
        for field in section.fields:
            spin = self._build_field_spinbox(section, field)
            self._spinboxes[(section.key, field.key)] = spin
            label = f"{field.label} ({field.unit})" if field.unit else field.label
            form.addRow(label, spin)
            if field.help:
                spin.setToolTip(field.help)
        return group

    def _build_field_spinbox(self, section, field):
        valor = self._draft[section.key][field.key]
        if field.kind == "int":
            spin = QSpinBox()
            minimo = 0 if field.minimum is None else int(field.minimum)
            maximo = 0 if field.maximum is None else int(field.maximum)
            spin.setRange(minimo, maximo)
            spin.setValue(int(valor))
        else:
            spin = QDoubleSpinBox()
            spin.setDecimals(field.decimals)
            spin.setRange(
                field.minimum if field.minimum is not None else -1e9,
                field.maximum if field.maximum is not None else 1e9,
            )
            spin.setSingleStep(10 ** (-field.decimals) if field.decimals else 1.0)
            spin.setValue(float(valor))
        if field.unit:
            spin.setSuffix(f" {field.unit}")
        spin.valueChanged.connect(lambda value, s=section, f=field: self._on_field_changed(s, f, value))
        return spin

    def _on_field_changed(self, section, field, value):
        self._draft[section.key][field.key] = value
        self._mark_dirty()

    # --- guardado explícito: los cambios se acumulan en self._draft y no
    # tocan disco hasta que se pulsa "Guardar" ---

    def _build_save_bar(self):
        self._save_button = AppSaveButton("Guardar")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._on_save_clicked)

        discard_button = AppButton("Descartar cambios", color="#8a8a8a")
        discard_button.clicked.connect(self._on_discard_clicked)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(discard_button)
        row.addWidget(self._save_button)
        return row

    def _mark_dirty(self):
        self._dirty = True
        self._save_button.setEnabled(True)

    def _on_save_clicked(self):
        if self._draft == self._controller.settings.as_dict():
            push(Module.FERLO, catalog.config_unchanged())
            return

        settings = Settings(self._draft)
        save_settings(settings)
        self._controller.reload()
        self._dirty = False
        self._save_button.setEnabled(False)

        if settings.validation_warnings:
            push(Module.FERLO, catalog.config_out_of_range(settings.validation_warnings))
        else:
            announce(agent_logger(), catalog.config_saved())

    def _on_discard_clicked(self):
        self._draft = self._controller.settings.as_dict()
        for (section_key, field_key), spin in self._spinboxes.items():
            spin.blockSignals(True)
            spin.setValue(self._draft[section_key][field_key])
            spin.blockSignals(False)
        self._entrada_edit.setText(self._draft["paths"]["entrada"])
        self._archivo_edit.setText(self._draft["paths"]["archivo"])
        self._dirty = False
        self._save_button.setEnabled(False)

    # --- programas de consigna: sin Excel de origen que portar (ver
    # logic/analysis/programs.py), se gestionan a mano ---

    def _build_programs_group(self):
        group = QGroupBox("Programas de consigna")

        self._programs_table = QTableWidget(0, 5)
        self._programs_table.setHorizontalHeaderLabels(
            ["Código", "Nombre", "Temperatura (°C)", "Tiempo (min)", "Activo"]
        )
        self._programs_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._programs_table.horizontalHeader().setSectionResizeMode(
            _COL_NAME, QHeaderView.ResizeMode.Stretch
        )
        self._programs_table.verticalHeader().setVisible(False)
        self._programs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._programs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._programs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_button = AppAddButton("Añadir / editar")
        add_button.clicked.connect(self._on_add_program)
        deactivate_button = AppButton("Activar/desactivar seleccionado")
        deactivate_button.clicked.connect(self._on_toggle_active)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(add_button)
        buttons_row.addWidget(deactivate_button)
        buttons_row.addStretch()

        layout = QVBoxLayout(group)
        layout.addWidget(self._programs_table)
        layout.addLayout(buttons_row)
        return group

    def _repaint_programs_table(self):
        table = self._programs_table
        current_row = table.currentRow()

        programas = self._controller.list_programs(include_inactive=True)
        table.setRowCount(0)
        for programa in programas:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, _COL_CODE, QTableWidgetItem(programa.display_code))
            table.setItem(row, _COL_NAME, QTableWidgetItem(programa.name))
            table.setItem(row, _COL_TEMP, QTableWidgetItem(f"{programa.target_temperature_c:.1f}"))
            table.setItem(row, _COL_TIME, QTableWidgetItem(f"{programa.target_time_min:.1f}"))
            table.setItem(row, _COL_ACTIVE, QTableWidgetItem("Sí" if programa.is_active else "No"))

        if 0 <= current_row < table.rowCount():
            table.selectRow(current_row)

    def _on_add_program(self):
        dialog = _ProgramDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            programa = dialog.value()
            if programa is None:
                push(Module.FERLO, catalog.program_code_required())
                return
            self._controller.upsert_program(programa)
            self._repaint_programs_table()
            announce(agent_logger(), catalog.program_saved(programa.code))

    def _on_toggle_active(self):
        row = self._programs_table.currentRow()
        if row < 0:
            return
        codigo = int(self._programs_table.item(row, _COL_CODE).text())
        activo_ahora = self._programs_table.item(row, _COL_ACTIVE).text() == "Sí"
        self._controller.set_program_active(codigo, not activo_ahora)
        self._repaint_programs_table()


class _ProgramDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Programa de consigna")

        self._code_spin = QSpinBox()
        self._code_spin.setRange(1, 999)

        self._name_edit = QLineEdit()

        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 150.0)
        self._temp_spin.setDecimals(1)
        self._temp_spin.setSuffix(" °C")

        self._time_spin = QDoubleSpinBox()
        self._time_spin.setRange(0.0, 600.0)
        self._time_spin.setDecimals(1)
        self._time_spin.setSuffix(" min")

        self._active_checkbox = QCheckBox("Activo")
        self._active_checkbox.setChecked(True)

        form = QFormLayout()
        form.addRow("Código:", self._code_spin)
        form.addRow("Nombre:", self._name_edit)
        form.addRow("Temperatura de consigna:", self._temp_spin)
        form.addRow("Tiempo de consigna:", self._time_spin)
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
            target_temperature_c=self._temp_spin.value(),
            target_time_min=self._time_spin.value(),
            is_active=self._active_checkbox.isChecked(),
        )
