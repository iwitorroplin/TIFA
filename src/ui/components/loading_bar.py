from __future__ import annotations

from PySide6.QtWidgets import QProgressBar

_DEFAULT_COLOR = "#4d88cb"


class LoadingBar(QProgressBar):
    """Barra de progreso con el estilo de la app. Arranca en modo indeterminado
    (no se sabe cuánto queda); usa `set_progress` en cuanto se conozca el avance real."""

    def __init__(self, color: str = _DEFAULT_COLOR, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(8)
        self.setStyleSheet(
            f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #2a2d31;
            }}
            QProgressBar::chunk {{
                border-radius: 4px;
                background-color: {color};
            }}
            """
        )
        self.set_indeterminate()

    def set_indeterminate(self) -> None:
        """Modo "ocupado": no se conoce el avance real, solo que algo está pasando."""
        self.setRange(0, 0)

    def set_progress(self, value: int, maximum: int = 100) -> None:
        """Modo con avance real conocido, de 0 a `maximum`."""
        self.setRange(0, maximum)
        self.setValue(value)
