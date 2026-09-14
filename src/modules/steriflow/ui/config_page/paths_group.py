from PySide6.QtWidgets import QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QWidget

from src.shared.ui.components.app_button import AppButton


class PathsGroup(QGroupBox):
    """Grupo "Rutas": carpeta raíz local y de servidor. Cambios puntuales, se
    notifican vía `on_change` para que la página marque el borrador sucio."""

    def __init__(self, presenter, on_change, parent=None):
        super().__init__("Rutas", parent)
        self._presenter = presenter
        self._on_change = on_change

        self._local_root_edit = QLineEdit()
        self._local_root_edit.editingFinished.connect(self._on_local_root_edited)

        self._server_root_edit = QLineEdit()
        self._server_root_edit.editingFinished.connect(self._on_server_root_edited)

        layout = QFormLayout(self)
        layout.addRow(
            "Carpeta raíz local:",
            self._build_path_row(self._local_root_edit, self._on_local_root_edited),
        )
        layout.addRow(
            "Carpeta raíz de servidor:",
            self._build_path_row(self._server_root_edit, self._on_server_root_edited),
        )

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
        self._on_change()

    def _on_server_root_edited(self):
        self._presenter.set_server_root(self._server_root_edit.text().strip())
        self._on_change()

    def repaint(self):
        self._local_root_edit.setText(self._presenter.local_root())
        self._server_root_edit.setText(self._presenter.server_root())
