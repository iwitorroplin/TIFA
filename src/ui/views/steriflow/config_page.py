from datetime import time
from pathlib import Path

from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.logic.steriflow.controller import SteriflowController
from src.logic.steriflow.config import (
    AutoclaveConfig,
    ScheduleConfig,
    SteriflowPaths,
    SteriflowSettings,
    save_settings,
)
from src.ui.components.app_button import AppButton


class SteriflowConfigPage(QWidget):
    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._controller = controller

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_paths_group())
        layout.addWidget(self._build_autoclaves_group())
        layout.addWidget(self._build_schedules_group())
        layout.addLayout(self._build_save_row())
        layout.addStretch()

        self._load_from_settings(controller.settings)

    def _build_paths_group(self):
        group = QGroupBox("Rutas")

        self._local_path_edit = QLineEdit()
        self._server_path_edit = QLineEdit()
        self._logs_path_edit = QLineEdit()

        group_layout = QFormLayout(group)
        group_layout.addRow(
            "Carpeta local (staging):",
            self._build_path_row(self._local_path_edit),
        )
        group_layout.addRow(
            "Carpeta de servidor (UNC):",
            self._build_path_row(self._server_path_edit),
        )
        group_layout.addRow(
            "Carpeta de logs:",
            self._build_path_row(self._logs_path_edit),
        )

        return group

    def _build_path_row(self, line_edit):
        row = QWidget()

        browse_button = AppButton("Seleccionar...")
        browse_button.clicked.connect(lambda: self._select_path(line_edit))

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_button)

        return row

    def _select_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", line_edit.text())
        if path:
            line_edit.setText(path)

    def _build_autoclaves_group(self):
        group = QGroupBox("Autoclaves")

        self._autoclaves_table = QTableWidget(0, 3)
        self._autoclaves_table.setHorizontalHeaderLabels(["Nombre", "IP", "Activo"])
        self._autoclaves_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._autoclaves_table.verticalHeader().setVisible(False)
        self._autoclaves_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._autoclaves_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._autoclaves_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_button = AppButton("Añadir fila")
        add_button.clicked.connect(self._add_autoclave_row)

        remove_button = AppButton("Quitar seleccionado", color="#e20c0c")
        remove_button.clicked.connect(self._remove_selected_autoclave_row)

        edit_button = AppButton("Editar seleccionado")
        edit_button.clicked.connect(self._edit_selected_autoclave_row)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(remove_button)
        buttons_layout.addWidget(edit_button)

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._autoclaves_table)
        group_layout.addLayout(buttons_layout)

        return group

    def _add_autoclave_row(self):
        dialog = _AutoclaveDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, ip, active = dialog.values()
            row = self._autoclaves_table.rowCount()
            self._autoclaves_table.insertRow(row)
            self._set_autoclave_row(row, name, ip, active)

    def _remove_selected_autoclave_row(self):
        row = self._autoclaves_table.currentRow()
        if row >= 0:
            self._autoclaves_table.removeRow(row)

    def _edit_selected_autoclave_row(self):
        row = self._autoclaves_table.currentRow()
        if row < 0:
            return

        name = self._autoclaves_table.item(row, 0).text()
        ip = self._autoclaves_table.item(row, 1).text()
        active = self._autoclaves_table.item(row, 2).checkState() == Qt.CheckState.Checked

        dialog = _AutoclaveDialog(self, name=name, ip=ip, active=active)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, ip, active = dialog.values()
            self._set_autoclave_row(row, name, ip, active)

    def _set_autoclave_row(self, row, name, ip, active):
        self._autoclaves_table.setItem(row, 0, QTableWidgetItem(name))
        self._autoclaves_table.setItem(row, 1, QTableWidgetItem(ip))

        active_item = QTableWidgetItem()
        active_item.setFlags(active_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        active_item.setCheckState(Qt.CheckState.Checked if active else Qt.CheckState.Unchecked)
        self._autoclaves_table.setItem(row, 2, active_item)

    def _build_schedules_group(self):
        group = QGroupBox("Horarios")

        self._schedules_table = QTableWidget(0, 1)
        self._schedules_table.setHorizontalHeaderLabels(["Hora"])
        self._schedules_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._schedules_table.verticalHeader().setVisible(False)
        self._schedules_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._schedules_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._schedules_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_button = AppButton("Añadir fila")
        add_button.clicked.connect(self._add_schedule_row)

        remove_button = AppButton("Quitar seleccionado", color="#e20c0c")
        remove_button.clicked.connect(self._remove_selected_schedule_row)

        edit_button = AppButton("Editar seleccionado")
        edit_button.clicked.connect(self._edit_selected_schedule_row)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(remove_button)
        buttons_layout.addWidget(edit_button)

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._schedules_table)
        group_layout.addLayout(buttons_layout)

        return group

    def _add_schedule_row(self):
        dialog = _ScheduleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = self._schedules_table.rowCount()
            self._schedules_table.insertRow(row)
            self._set_schedule_row(row, dialog.value())

    def _remove_selected_schedule_row(self):
        row = self._schedules_table.currentRow()
        if row >= 0:
            self._schedules_table.removeRow(row)

    def _edit_selected_schedule_row(self):
        row = self._schedules_table.currentRow()
        if row < 0:
            return

        time = QTime.fromString(self._schedules_table.item(row, 0).text(), "HH:mm")

        dialog = _ScheduleDialog(self, time=time)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_schedule_row(row, dialog.value())

    def _set_schedule_row(self, row, time):
        time_item = QTableWidgetItem(time.toString("HH:mm"))
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._schedules_table.setItem(row, 0, time_item)

    def _build_save_row(self):
        row_layout = QHBoxLayout()

        save_button = AppButton("Guardar")
        save_button.clicked.connect(self._on_save_clicked)

        row_layout.addStretch()
        row_layout.addWidget(save_button)

        return row_layout

    def _load_from_settings(self, settings: SteriflowSettings):
        self._local_path_edit.setText(str(settings.paths.local_root))
        self._server_path_edit.setText(str(settings.paths.server_root))
        self._logs_path_edit.setText(str(settings.paths.logs_root))

        self._autoclaves_table.setRowCount(0)
        for autoclave in settings.autoclaves:
            row = self._autoclaves_table.rowCount()
            self._autoclaves_table.insertRow(row)
            self._set_autoclave_row(row, autoclave.name, autoclave.ip, autoclave.active)

        self._schedules_table.setRowCount(0)
        for hour in settings.schedule.execution_hours:
            row = self._schedules_table.rowCount()
            self._schedules_table.insertRow(row)
            self._set_schedule_row(row, QTime(hour.hour, hour.minute))

    def _on_save_clicked(self):
        autoclaves = [
            AutoclaveConfig(
                name=self._autoclaves_table.item(row, 0).text(),
                ip=self._autoclaves_table.item(row, 1).text(),
                active=self._autoclaves_table.item(row, 2).checkState() == Qt.CheckState.Checked,
            )
            for row in range(self._autoclaves_table.rowCount())
        ]

        execution_hours = [
            time.fromisoformat(self._schedules_table.item(row, 0).text())
            for row in range(self._schedules_table.rowCount())
        ]

        if not execution_hours:
            QMessageBox.warning(self, "Backup", "Añade al menos un horario antes de guardar.")
            return

        settings = SteriflowSettings(
            paths=SteriflowPaths(
                local_root=Path(self._local_path_edit.text()),
                server_root=Path(self._server_path_edit.text()),
                logs_root=Path(self._logs_path_edit.text()),
            ),
            autoclaves=autoclaves,
            schedule=ScheduleConfig(execution_hours=execution_hours),
        )

        save_settings(settings)
        self._controller.reload()
        self._load_from_settings(self._controller.settings)
        QMessageBox.information(self, "Backup", "Configuración guardada.")


class _AutoclaveDialog(QDialog):
    def __init__(self, parent=None, name="", ip="", active=True):
        super().__init__(parent)
        self.setWindowTitle("Autoclave")

        self._name_edit = QLineEdit(name)
        self._ip_edit = QLineEdit(ip)
        self._active_checkbox = QCheckBox("Activo")
        self._active_checkbox.setChecked(active)

        form_layout = QFormLayout()
        form_layout.addRow("Nombre:", self._name_edit)
        form_layout.addRow("IP:", self._ip_edit)
        form_layout.addRow(self._active_checkbox)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def values(self):
        return self._name_edit.text(), self._ip_edit.text(), self._active_checkbox.isChecked()


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
