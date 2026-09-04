from datetime import time
from pathlib import Path

from PySide6.QtCore import QTime, QTimer, Qt
from PySide6.QtGui import QIcon
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

from src.modules.steriflow.logic.controller import SteriflowController
from src.modules.steriflow.logic.config import (
    AutoclaveConfig,
    ScheduleConfig,
    SteriflowPaths,
    SteriflowSettings,
    save_settings,
)
from src.modules.steriflow.logic.network import MachineStatus
from src.shared.assets.resources import MATERIA_GREEN_IMAGE, MATERIA_RED_IMAGE, MATERIA_YELLOW_IMAGE
from src.shared.ui.components.app_button import AppButton
from src.modules.steriflow.ui.status_checker import AutoclaveStatusChecker

# Índices de columna de la tabla de autoclaves. Explícitos porque "Activo" es
# un checkbox: leerlo de la columna equivocada (p. ej. tras insertar una
# columna nueva) no da un error, da un QTableWidgetItem sin checkState que se
# interpreta como "inactivo" en silencio.
_COL_NAME = 0
_COL_IP = 1
_COL_PATH = 2
_COL_LOCAL = 3
_COL_BACKUP = 4
_COL_ACTIVE = 5
_COL_STATUS = 6

_STATUS_REFRESH_INTERVAL_MS = 30_000


class SteriflowConfigPage(QWidget):
    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._controller = controller

        self._status_checker = AutoclaveStatusChecker(self)
        self._status_checker.checked.connect(self._on_status_checked)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(_STATUS_REFRESH_INTERVAL_MS)
        self._status_timer.timeout.connect(self._refresh_statuses)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_paths_group())
        layout.addWidget(self._build_autoclaves_group())
        layout.addWidget(self._build_schedules_group())
        layout.addStretch()

        self._load_from_settings(controller.settings)

    def showEvent(self, event):
        super().showEvent(event)
        self._status_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._status_timer.stop()

    def _build_paths_group(self):
        group = QGroupBox("Rutas")

        self._logs_path_edit = QLineEdit()
        self._logs_path_edit.editingFinished.connect(self._persist)

        self._local_root_edit = QLineEdit()
        self._local_root_edit.editingFinished.connect(self._persist)

        self._server_root_edit = QLineEdit()
        self._server_root_edit.editingFinished.connect(self._persist)

        group_layout = QFormLayout(group)
        group_layout.addRow(
            "Carpeta de logs:",
            self._build_path_row(self._logs_path_edit),
        )
        group_layout.addRow(
            "Carpeta raíz local:",
            self._build_path_row(self._local_root_edit),
        )
        group_layout.addRow(
            "Carpeta raíz de servidor:",
            self._build_path_row(self._server_root_edit),
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
            self._persist()

    def _build_autoclaves_group(self):
        group = QGroupBox("Autoclaves")

        self._autoclaves_table = QTableWidget(0, 7)
        self._autoclaves_table.setHorizontalHeaderLabels(
            ["Nombre", "IP", "Carpeta origen", "Carpeta local", "Carpeta backup", "Activo", "Estado"]
        )
        self._autoclaves_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._autoclaves_table.horizontalHeader().setSectionResizeMode(
            _COL_PATH, QHeaderView.ResizeMode.Stretch
        )
        self._autoclaves_table.horizontalHeader().setSectionResizeMode(
            _COL_LOCAL, QHeaderView.ResizeMode.Stretch
        )
        self._autoclaves_table.horizontalHeader().setSectionResizeMode(
            _COL_BACKUP, QHeaderView.ResizeMode.Stretch
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
        buttons_layout.addStretch()

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._autoclaves_table)
        group_layout.addLayout(buttons_layout)

        return group

    def _add_autoclave_row(self):
        dialog = _AutoclaveDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, ip, path_folder, local_folder, backup_folder, active = dialog.values()
            row = self._autoclaves_table.rowCount()
            self._autoclaves_table.insertRow(row)
            self._set_autoclave_row(
                row,
                name=name,
                ip=ip,
                path_folder=path_folder,
                local_folder=local_folder,
                backup_folder=backup_folder,
                active=active,
            )
            self._persist()

    def _remove_selected_autoclave_row(self):
        row = self._autoclaves_table.currentRow()
        if row >= 0:
            self._autoclaves_table.removeRow(row)
            self._persist()

    def _edit_selected_autoclave_row(self):
        row = self._autoclaves_table.currentRow()
        if row < 0:
            return

        name = self._autoclaves_table.item(row, _COL_NAME).text()
        ip = self._autoclaves_table.item(row, _COL_IP).text()
        path_folder = self._autoclaves_table.item(row, _COL_PATH).text()
        local_folder = self._autoclaves_table.item(row, _COL_LOCAL).text()
        backup_folder = self._autoclaves_table.item(row, _COL_BACKUP).text()
        active = self._autoclaves_table.item(row, _COL_ACTIVE).checkState() == Qt.CheckState.Checked

        dialog = _AutoclaveDialog(
            self,
            name=name,
            ip=ip,
            path_folder=path_folder,
            local_folder=local_folder,
            backup_folder=backup_folder,
            active=active,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, ip, path_folder, local_folder, backup_folder, active = dialog.values()
            self._set_autoclave_row(
                row,
                name=name,
                ip=ip,
                path_folder=path_folder,
                local_folder=local_folder,
                backup_folder=backup_folder,
                active=active,
            )
            self._persist()

    def _set_autoclave_row(self, row, *, name, ip, path_folder, local_folder, backup_folder, active):
        self._autoclaves_table.setItem(row, _COL_NAME, QTableWidgetItem(name))
        self._autoclaves_table.setItem(row, _COL_IP, QTableWidgetItem(ip))

        path_item = QTableWidgetItem(path_folder)
        path_item.setToolTip(path_folder)
        self._autoclaves_table.setItem(row, _COL_PATH, path_item)

        local_item = QTableWidgetItem(local_folder)
        local_item.setToolTip(local_folder)
        self._autoclaves_table.setItem(row, _COL_LOCAL, local_item)

        backup_item = QTableWidgetItem(backup_folder)
        backup_item.setToolTip(backup_folder)
        self._autoclaves_table.setItem(row, _COL_BACKUP, backup_item)

        active_item = QTableWidgetItem()
        active_item.setFlags(active_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        active_item.setCheckState(Qt.CheckState.Checked if active else Qt.CheckState.Unchecked)
        self._autoclaves_table.setItem(row, _COL_ACTIVE, active_item)

        # El nombre/IP puede haber cambiado: el estado de red anterior ya no
        # es de fiar, se resetea aquí y se recalcula en segundo plano.
        status_item = QTableWidgetItem("Comprobando…")
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._autoclaves_table.setItem(row, _COL_STATUS, status_item)

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
        buttons_layout.addStretch()

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
            self._persist()

    def _remove_selected_schedule_row(self):
        row = self._schedules_table.currentRow()
        if row < 0:
            return

        if self._schedules_table.rowCount() <= 1:
            QMessageBox.warning(self, "Backup", "Debe quedar al menos un horario configurado.")
            return

        self._schedules_table.removeRow(row)
        self._persist()

    def _edit_selected_schedule_row(self):
        row = self._schedules_table.currentRow()
        if row < 0:
            return

        time_value = QTime.fromString(self._schedules_table.item(row, 0).text(), "HH:mm")

        dialog = _ScheduleDialog(self, time=time_value)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_schedule_row(row, dialog.value())
            self._persist()

    def _set_schedule_row(self, row, time):
        time_item = QTableWidgetItem(time.toString("HH:mm"))
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._schedules_table.setItem(row, 0, time_item)

    def _load_from_settings(self, settings: SteriflowSettings):
        self._logs_path_edit.setText(str(settings.paths.logs_root))
        self._local_root_edit.setText(str(settings.paths.local_root))
        self._server_root_edit.setText(str(settings.paths.server_root))

        self._autoclaves_table.setRowCount(0)
        for autoclave in settings.autoclaves:
            row = self._autoclaves_table.rowCount()
            self._autoclaves_table.insertRow(row)
            self._set_autoclave_row(
                row,
                name=autoclave.name,
                ip=autoclave.ip,
                path_folder=autoclave.path_folder,
                local_folder=autoclave.local_folder,
                backup_folder=autoclave.backup_folder,
                active=autoclave.active,
            )

        self._schedules_table.setRowCount(0)
        for hour in settings.schedule.execution_hours:
            row = self._schedules_table.rowCount()
            self._schedules_table.insertRow(row)
            self._set_schedule_row(row, QTime(hour.hour, hour.minute))

        self._refresh_statuses()

    def _refresh_statuses(self):
        """Lanza un ping por autoclave en segundo plano (ver
        _AutoclaveStatusChecker): con timeout de 2 s por máquina, hacerlo en el
        hilo de la interfaz congelaría la pestaña varios segundos."""
        rows = [
            (
                self._autoclaves_table.item(row, _COL_NAME).text(),
                self._autoclaves_table.item(row, _COL_IP).text(),
            )
            for row in range(self._autoclaves_table.rowCount())
        ]
        self._status_checker.check(rows)

    def _on_status_checked(self, name, status: MachineStatus):
        row = self._find_autoclave_row(name)
        if row is None:
            return

        icon, text = {
            MachineStatus.ONLINE: (MATERIA_GREEN_IMAGE, "En línea"),
            MachineStatus.OFFLINE: (MATERIA_RED_IMAGE, "Apagada"),
            MachineStatus.CONNECTION_ERROR: (MATERIA_YELLOW_IMAGE, "Fallo de conexión"),
        }[status]
        status_item = QTableWidgetItem(QIcon(str(icon)), text)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._autoclaves_table.setItem(row, _COL_STATUS, status_item)

    def _find_autoclave_row(self, name):
        for row in range(self._autoclaves_table.rowCount()):
            if self._autoclaves_table.item(row, _COL_NAME).text() == name:
                return row
        return None

    def _persist(self):
        """Guarda de inmediato el estado actual de la página: cada acción puntual
        (elegir una carpeta, aceptar el diálogo de autoclave/horario, quitar una
        fila) ya deja la configuración guardada — no hay un botón "Guardar" aparte."""
        logs_text = self._logs_path_edit.text().strip()
        if not logs_text:
            QMessageBox.warning(self, "Backup", "La carpeta de logs es obligatoria.")
            return

        local_root_text = self._local_root_edit.text().strip()
        if not local_root_text:
            QMessageBox.warning(self, "Backup", "La carpeta raíz local es obligatoria.")
            return

        server_root_text = self._server_root_edit.text().strip()
        if not server_root_text:
            QMessageBox.warning(self, "Backup", "La carpeta raíz de servidor es obligatoria.")
            return

        autoclaves = [
            AutoclaveConfig(
                name=self._autoclaves_table.item(row, _COL_NAME).text(),
                ip=self._autoclaves_table.item(row, _COL_IP).text(),
                path_folder=self._autoclaves_table.item(row, _COL_PATH).text().strip(),
                local_folder=self._autoclaves_table.item(row, _COL_LOCAL).text().strip(),
                backup_folder=self._autoclaves_table.item(row, _COL_BACKUP).text().strip(),
                active=self._autoclaves_table.item(row, _COL_ACTIVE).checkState() == Qt.CheckState.Checked,
            )
            for row in range(self._autoclaves_table.rowCount())
        ]

        execution_hours = [
            time.fromisoformat(self._schedules_table.item(row, 0).text())
            for row in range(self._schedules_table.rowCount())
        ]

        if not execution_hours:
            QMessageBox.warning(self, "Backup", "Debe quedar al menos un horario configurado.")
            return

        settings = SteriflowSettings(
            paths=SteriflowPaths(
                logs_root=Path(logs_text),
                local_root=Path(local_root_text),
                server_root=Path(server_root_text),
            ),
            autoclaves=autoclaves,
            schedule=ScheduleConfig(execution_hours=execution_hours),
        )

        save_settings(settings)
        self._controller.reload()
        self._load_from_settings(self._controller.settings)


class _AutoclaveDialog(QDialog):
    def __init__(
        self,
        parent=None,
        name="",
        ip="",
        path_folder="",
        local_folder="",
        backup_folder="",
        active=True,
    ):
        super().__init__(parent)
        self.setWindowTitle("Autoclave")

        self._name_edit = QLineEdit(name)
        self._ip_edit = QLineEdit(ip)

        self._path_folder_edit = QLineEdit(path_folder)
        self._path_folder_edit.setPlaceholderText(r"\\AUTOCLAVE6\Export")
        self._path_folder_edit.setMinimumWidth(220)
        path_row = self._build_path_row(self._path_folder_edit)

        self._local_folder_edit = QLineEdit(local_folder)
        self._local_folder_edit.setPlaceholderText(r"C:\TIFA\data\steriflow\local\AUTOCLAVE6")
        self._local_folder_edit.setMinimumWidth(220)
        local_row = self._build_path_row(self._local_folder_edit)

        self._backup_folder_edit = QLineEdit(backup_folder)
        self._backup_folder_edit.setPlaceholderText(r"\\SERVIDOR\Backups\AUTOCLAVE6")
        self._backup_folder_edit.setMinimumWidth(220)
        backup_row = self._build_path_row(self._backup_folder_edit)

        self._active_checkbox = QCheckBox("Activo")
        self._active_checkbox.setChecked(active)

        form_layout = QFormLayout()
        form_layout.addRow("Nombre:", self._name_edit)
        form_layout.addRow("IP:", self._ip_edit)
        form_layout.addRow("Carpeta origen (UNC):", path_row)
        form_layout.addRow("Carpeta local:", local_row)
        form_layout.addRow("Carpeta de backup (servidor):", backup_row)
        form_layout.addRow(self._active_checkbox)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

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
        # El origen es la propia autoclave (red): si está apagada, el
        # explorador puede tardar en abrir. Lo mismo si el servidor de backup
        # no responde. La carpeta local no tiene ese problema (es del PC de TIFA).
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", line_edit.text())
        if path:
            line_edit.setText(path)

    def accept(self):
        if not self._path_folder_edit.text().strip():
            QMessageBox.warning(self, "Autoclave", "La carpeta origen es obligatoria.")
            return
        if not self._local_folder_edit.text().strip():
            QMessageBox.warning(self, "Autoclave", "La carpeta local es obligatoria.")
            return
        if not self._backup_folder_edit.text().strip():
            QMessageBox.warning(self, "Autoclave", "La carpeta de backup es obligatoria.")
            return
        super().accept()

    def values(self):
        return (
            self._name_edit.text(),
            self._ip_edit.text(),
            self._path_folder_edit.text().strip(),
            self._local_folder_edit.text().strip(),
            self._backup_folder_edit.text().strip(),
            self._active_checkbox.isChecked(),
        )


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
