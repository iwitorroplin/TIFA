from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout


class ColumnsDialog(QDialog):
    """Modal "Columnas de la tabla de ciclos": un checkbox por columna
    configurable. Igual que SchedulesDialog, escribe directo en el borrador
    del presenter; "Cerrar" no descarta nada, el guardado real es aparte."""

    def __init__(self, presenter, on_change, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Columnas de la tabla de ciclos")
        self._presenter = presenter
        self._on_change = on_change

        layout = QVBoxLayout(self)

        self._checkboxes: dict[str, QCheckBox] = {}
        for col in self._presenter.configurable_columns():
            checkbox = QCheckBox(col.header)
            checkbox.toggled.connect(lambda checked, key=col.key: self._on_toggled(key, checked))
            self._checkboxes[col.key] = checkbox
            layout.addWidget(checkbox)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        close_box.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(close_box)

        self._repaint()

    def _on_toggled(self, key, checked):
        self._presenter.set_column_visible(key, checked)
        self._on_change()

    def _repaint(self):
        for key, checkbox in self._checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(self._presenter.is_column_visible(key))
            checkbox.blockSignals(False)
