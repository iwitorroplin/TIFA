from PySide6.QtWidgets import QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QWidget

from src.shared.paths import PROJECT_ROOT
from src.shared.ui.components.app_button import AppButton


class PathsGroup(QGroupBox):
    """Grupo "Carpetas": entrada (buzón transitorio) y archivo (mensual).
    No forman parte de `SETTINGS_SCHEMA` -son carpetas, no números con
    rango- y se editan aparte, igual que Steriflow edita sus rutas con un
    `QLineEdit` + "Seleccionar..."."""

    def __init__(self, draft: dict, on_change, parent=None):
        super().__init__("Carpetas", parent)
        self._draft = draft
        self._on_change = on_change

        self._entrada_edit = QLineEdit(draft["paths"]["entrada"])
        self._entrada_edit.editingFinished.connect(
            lambda: self._on_path_edited("entrada", self._entrada_edit)
        )
        self._archivo_edit = QLineEdit(draft["paths"]["archivo"])
        self._archivo_edit.editingFinished.connect(
            lambda: self._on_path_edited("archivo", self._archivo_edit)
        )

        form = QFormLayout(self)
        form.addRow("Entrada (buzón transitorio):", self._path_row(self._entrada_edit))
        form.addRow("Archivo (mensual que mantiene TIFA):", self._path_row(self._archivo_edit))

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
        self._on_change()

    def repaint(self):
        self._entrada_edit.setText(self._draft["paths"]["entrada"])
        self._archivo_edit.setText(self._draft["paths"]["archivo"])
