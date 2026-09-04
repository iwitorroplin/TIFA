from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from src.shared.ui.components.loading_bar import LoadingBar


class LoadingDialog(QDialog):
    """Ventana modal que bloquea la interfaz mientras dura una operación larga
    (p. ej. un backup manual). Sin botón de cerrar: quien la abre es quien la
    cierra desde código (`accept`/`close`) al terminar la operación."""

    def __init__(self, parent=None, message: str = "Cargando..."):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setModal(True)
        self.setFixedWidth(320)

        self._label = QLabel(message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._bar = LoadingBar()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(self._label)
        layout.addWidget(self._bar)

    def set_message(self, message: str) -> None:
        self._label.setText(message)

    def set_progress(self, value: int, maximum: int = 100) -> None:
        self._bar.set_progress(value, maximum)

    def set_indeterminate(self) -> None:
        self._bar.set_indeterminate()
