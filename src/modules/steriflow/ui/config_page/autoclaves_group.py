from PySide6.QtCore import Qt
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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.steriflow.logic.config import AutoclaveConfig, default_autoclave_code
from src.modules.steriflow.logic.settings_editor import validate_autoclave
from src.modules.steriflow.messages import catalog
from src.shared.messages.notice import push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppAddButton, AppButton, AppDeleteButton, AppModifyButton

# Índices de columna de la tabla de autoclaves. Explícitos porque "Activo" es
# un checkbox: leerlo de la columna equivocada (p. ej. tras insertar una
# columna nueva) no da un error, da un QTableWidgetItem sin checkState que se
# interpreta como "inactivo" en silencio.
_COL_NAME = 0
_COL_IP = 1
_COL_CODE = 2
_COL_PATH = 3
_COL_LOCAL = 4
_COL_BACKUP = 5
_COL_ACTIVE = 6


class AutoclavesGroup(QGroupBox):
    """Grupo "Autoclaves": tabla + alta/edición/baja mediante `_AutoclaveDialog`."""

    def __init__(self, view_model, on_change, parent=None):
        super().__init__("Autoclaves", parent)
        self._view_model = view_model
        self._on_change = on_change

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Nombre", "IP", "Código", "Carpeta origen", "Carpeta local", "Carpeta backup",
             "Activo"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_PATH, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_LOCAL, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_BACKUP, QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

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

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(buttons_layout)

    def _add_row(self):
        dialog = _AutoclaveDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._view_model.add_autoclave(_autoclave_from_dialog(dialog))
            self._on_change()

    def _remove_selected_row(self):
        row = self._table.currentRow()
        if row >= 0:
            self._view_model.remove_autoclave(row)
            self._on_change()

    def _edit_selected_row(self):
        row = self._table.currentRow()
        if row < 0:
            return

        autoclave = self._view_model.autoclaves()[row]
        dialog = _AutoclaveDialog(
            self,
            name=autoclave.name,
            ip=autoclave.ip,
            code=autoclave.code,
            report_code=autoclave.report_code,
            path_folder=autoclave.path_folder,
            local_folder=autoclave.local_folder,
            backup_folder=autoclave.backup_folder,
            active=autoclave.active,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._view_model.update_autoclave(row, _autoclave_from_dialog(dialog))
            self._on_change()

    def repaint(self):
        table = self._table
        current_row = table.currentRow()

        table.setRowCount(0)
        for autoclave in self._view_model.autoclaves():
            row = table.rowCount()
            table.insertRow(row)
            self._set_row(row, autoclave)

        if 0 <= current_row < table.rowCount():
            table.selectRow(current_row)

    def _set_row(self, row, autoclave: AutoclaveConfig):
        table = self._table
        table.setItem(row, _COL_NAME, QTableWidgetItem(autoclave.name))
        table.setItem(row, _COL_IP, QTableWidgetItem(autoclave.ip))

        # Los dos números en una sola celda, y solo cuando difieren: que la
        # máquina imprima otro código es la excepción, no la norma, y merece
        # verse de un vistazo justo donde se configura.
        code_item = QTableWidgetItem(
            str(autoclave.code)
            if autoclave.report_code == autoclave.code
            else f"{autoclave.code} (informa {autoclave.report_code})"
        )
        code_item.setToolTip(
            "Código real de la autoclave y, entre paréntesis, el que imprime "
            "en sus informes cuando no coincide."
        )
        table.setItem(row, _COL_CODE, code_item)

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


def _autoclave_from_dialog(dialog: "_AutoclaveDialog") -> AutoclaveConfig:
    name, ip, code, report_code, path_folder, local_folder, backup_folder, active = dialog.values()
    # Un alta nueva llega con los códigos a 0 (el spin arranca vacío): se
    # deducen del nombre, igual que hace `load_settings` con un yaml antiguo,
    # en vez de guardar una autoclave con código 0.
    code = code or default_autoclave_code(name)
    return AutoclaveConfig(
        name=name,
        ip=ip,
        code=code,
        report_code=report_code or code,
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
        code=0,
        report_code=0,
        path_folder="",
        local_folder="",
        backup_folder="",
        active=True,
    ):
        super().__init__(parent)
        self.setWindowTitle("Autoclave")

        self._name_edit = QLineEdit(name)
        self._ip_edit = QLineEdit(ip)

        self._code_spin = QSpinBox()
        self._code_spin.setRange(0, 99)
        self._code_spin.setValue(code)
        self._code_spin.setToolTip(
            "El número real de esta autoclave. Es el que se guarda con cada ciclo."
        )

        self._report_code_spin = QSpinBox()
        self._report_code_spin.setRange(0, 99)
        self._report_code_spin.setValue(report_code or code)
        self._report_code_spin.setToolTip(
            "El número que esta máquina imprime en sus PDF ('Cód. Autoclave').\n"
            "Normalmente es el mismo; la AUTOCLAVE8 imprime 10 por un error\n"
            "histórico que no se puede corregir en los informes ya emitidos."
        )

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
        form_layout.addRow("Código real:", self._code_spin)
        form_layout.addRow("Código que imprime en el PDF:", self._report_code_spin)
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
            push(Module.STERIFLOW, catalog.autoclave_issue(issue))
            return
        super().accept()

    def values(self):
        return (
            self._name_edit.text(),
            self._ip_edit.text(),
            self._code_spin.value(),
            self._report_code_spin.value(),
            self._path_folder_edit.text().strip(),
            self._local_folder_edit.text().strip(),
            self._backup_folder_edit.text().strip(),
            self._active_checkbox.isChecked(),
        )
