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
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.modules.steriflow.logic.controller import SteriflowController
from src.modules.steriflow.logic.config import AutoclaveConfig
from src.modules.steriflow.logic.logs import agent_logger
from src.modules.steriflow.logic.network import MachineStatus
from src.modules.steriflow.logic.settings_editor import SaveStatus, SettingsIssue, validate_autoclave
from src.modules.steriflow.messages import catalog
from src.modules.steriflow.ui.config_presenter import SteriflowConfigPresenter
from src.shared.assets.resources import MATERIA_GREEN_IMAGE, MATERIA_RED_IMAGE, MATERIA_YELLOW_IMAGE
from src.shared.messages.notice import announce
from src.shared.ui import notices
from src.shared.ui.components.app_button import AppButton
from src.modules.steriflow.tasks.status_checker import AutoclaveStatusChecker

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

# La etiqueta de cada estado la da catalog.machine_status_label (compartida
# con el resumen de conectividad de home_page); el icono es decoración pura,
# se queda aquí.
_STATUS_ICONS = {
    MachineStatus.ONLINE: MATERIA_GREEN_IMAGE,
    MachineStatus.OFFLINE: MATERIA_RED_IMAGE,
    MachineStatus.CONNECTION_ERROR: MATERIA_YELLOW_IMAGE,
}

_STATUS_REFRESH_INTERVAL_MS = 30_000


class SteriflowConfigPage(QWidget):
    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._presenter = SteriflowConfigPresenter(controller)

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

        self._repaint()
        self._refresh_statuses()

    def showEvent(self, event):
        super().showEvent(event)
        self._status_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._status_timer.stop()

    def _build_paths_group(self):
        group = QGroupBox("Rutas")

        self._local_root_edit = QLineEdit()
        self._local_root_edit.editingFinished.connect(self._on_local_root_edited)

        self._server_root_edit = QLineEdit()
        self._server_root_edit.editingFinished.connect(self._on_server_root_edited)

        group_layout = QFormLayout(group)
        group_layout.addRow(
            "Carpeta raíz local:",
            self._build_path_row(self._local_root_edit, self._on_local_root_edited),
        )
        group_layout.addRow(
            "Carpeta raíz de servidor:",
            self._build_path_row(self._server_root_edit, self._on_server_root_edited),
        )

        return group

    def _build_path_row(self, line_edit, on_change):
        row = QWidget()

        browse_button = AppButton("Seleccionar...")
        browse_button.clicked.connect(lambda: self._select_path(line_edit, on_change))

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_button)

        return row

    def _select_path(self, line_edit, on_change):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", line_edit.text())
        if path:
            line_edit.setText(path)
            on_change()

    def _on_local_root_edited(self):
        self._presenter.set_local_root(self._local_root_edit.text().strip())
        self._persist()

    def _on_server_root_edited(self):
        self._presenter.set_server_root(self._server_root_edit.text().strip())
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
            self._presenter.add_autoclave(_autoclave_from_dialog(dialog))
            self._persist()

    def _remove_selected_autoclave_row(self):
        row = self._autoclaves_table.currentRow()
        if row >= 0:
            self._presenter.remove_autoclave(row)
            self._persist()

    def _edit_selected_autoclave_row(self):
        row = self._autoclaves_table.currentRow()
        if row < 0:
            return

        autoclave = self._presenter.autoclaves()[row]
        dialog = _AutoclaveDialog(
            self,
            name=autoclave.name,
            ip=autoclave.ip,
            path_folder=autoclave.path_folder,
            local_folder=autoclave.local_folder,
            backup_folder=autoclave.backup_folder,
            active=autoclave.active,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.update_autoclave(row, _autoclave_from_dialog(dialog))
            self._persist()

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
            self._presenter.add_hour(dialog.value().toPython())
            self._persist()

    def _remove_selected_schedule_row(self):
        row = self._schedules_table.currentRow()
        if row < 0:
            return

        if not self._presenter.can_remove_hour():
            notices.show(self, catalog.settings_issue(SettingsIssue.AT_LEAST_ONE_SCHEDULE))
            return

        self._presenter.remove_hour(row)
        self._persist()

    def _edit_selected_schedule_row(self):
        row = self._schedules_table.currentRow()
        if row < 0:
            return

        hour = self._presenter.hours()[row]
        dialog = _ScheduleDialog(self, time=QTime(hour.hour, hour.minute))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._presenter.update_hour(row, dialog.value().toPython())
            self._persist()

    def _repaint(self):
        """Repinta todo desde el presenter, nunca al revés: así la tabla
        nunca puede desincronizarse de lo que hay realmente en el borrador
        (ver el riesgo de índices desalineados en el histórico del refactor).
        Única excepción: la celda de estado de red, que llega por señal
        (`_on_status_checked`) y se actualiza sola, sin repintar la tabla
        entera en cada ping."""
        self._local_root_edit.setText(self._presenter.local_root())
        self._server_root_edit.setText(self._presenter.server_root())
        self._repaint_autoclaves_table()
        self._repaint_schedules_table()

    def _repaint_autoclaves_table(self):
        table = self._autoclaves_table
        current_row = table.currentRow()

        table.setRowCount(0)
        for autoclave in self._presenter.autoclaves():
            row = table.rowCount()
            table.insertRow(row)
            self._set_autoclave_row(row, autoclave)

        if 0 <= current_row < table.rowCount():
            table.selectRow(current_row)

    def _set_autoclave_row(self, row, autoclave: AutoclaveConfig):
        table = self._autoclaves_table
        table.setItem(row, _COL_NAME, QTableWidgetItem(autoclave.name))
        table.setItem(row, _COL_IP, QTableWidgetItem(autoclave.ip))

        path_item = QTableWidgetItem(autoclave.path_folder)
        path_item.setToolTip(autoclave.path_folder)
        table.setItem(row, _COL_PATH, path_item)

        local_item = QTableWidgetItem(autoclave.local_folder)
        local_item.setToolTip(autoclave.local_folder)
        table.setItem(row, _COL_LOCAL, local_item)

        backup_item = QTableWidgetItem(autoclave.backup_folder)
        backup_item.setToolTip(autoclave.backup_folder)
        table.setItem(row, _COL_BACKUP, backup_item)

        active_item = QTableWidgetItem()
        active_item.setFlags(active_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        active_item.setCheckState(Qt.CheckState.Checked if autoclave.active else Qt.CheckState.Unchecked)
        table.setItem(row, _COL_ACTIVE, active_item)

        self._set_status_cell(row, autoclave.name)

    def _set_status_cell(self, row, name):
        status = self._presenter.status_of(name)
        if status is None:
            status_item = QTableWidgetItem("Comprobando…")
        else:
            status_item = QTableWidgetItem(
                QIcon(str(_STATUS_ICONS[status])), catalog.machine_status_label(status)
            )
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._autoclaves_table.setItem(row, _COL_STATUS, status_item)

    def _repaint_schedules_table(self):
        table = self._schedules_table
        current_row = table.currentRow()

        table.setRowCount(0)
        for hour in self._presenter.hours():
            row = table.rowCount()
            table.insertRow(row)
            self._set_schedule_row(row, QTime(hour.hour, hour.minute))

        if 0 <= current_row < table.rowCount():
            table.selectRow(current_row)

    def _set_schedule_row(self, row, qtime):
        time_item = QTableWidgetItem(qtime.toString("HH:mm"))
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._schedules_table.setItem(row, 0, time_item)

    def _refresh_statuses(self):
        """Lanza un ping por autoclave en segundo plano (ver
        AutoclaveStatusChecker): con timeout de 2 s por máquina, hacerlo en el
        hilo de la interfaz congelaría la pestaña varios segundos."""
        self._status_checker.check(self._presenter.status_targets())

    def _on_status_checked(self, name, status: MachineStatus):
        self._presenter.set_status(name, status)
        row = self._find_autoclave_row(name)
        if row is not None:
            self._set_status_cell(row, name)

    def _find_autoclave_row(self, name):
        for row in range(self._autoclaves_table.rowCount()):
            if self._autoclaves_table.item(row, _COL_NAME).text() == name:
                return row
        return None

    def _persist(self):
        """Guarda de inmediato el estado actual del borrador: cada acción puntual
        (elegir una carpeta, aceptar el diálogo de autoclave/horario, quitar una
        fila) ya deja la configuración guardada — no hay un botón "Guardar" aparte."""
        outcome = self._presenter.save()
        self._repaint()

        if outcome.status is SaveStatus.INVALID:
            notices.show(self, catalog.settings_issue(outcome.issue))
            return
        if outcome.status is SaveStatus.SAVED:
            self._refresh_statuses()
            # Esta página no tiene botón "Guardar" -se persiste sola-, así que sin
            # este aviso no hay forma de saber que el cambio ha entrado. Y la línea
            # de log es la que explica meses después por qué el backup dejó de
            # copiar: alguien cambió una ruta tal día.
            announce(agent_logger(), catalog.settings_saved())


def _autoclave_from_dialog(dialog: "_AutoclaveDialog") -> AutoclaveConfig:
    name, ip, path_folder, local_folder, backup_folder, active = dialog.values()
    return AutoclaveConfig(
        name=name,
        ip=ip,
        path_folder=path_folder,
        local_folder=local_folder,
        backup_folder=backup_folder,
        active=active,
    )


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
        autoclave = _autoclave_from_dialog(self)
        issue = validate_autoclave(autoclave)
        if issue is not None:
            notices.show(self, catalog.autoclave_issue(issue))
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
