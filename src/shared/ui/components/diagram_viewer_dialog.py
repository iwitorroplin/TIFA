"""Ventana no modal que muestra un dibujo estatico (svg o raster) a modo de
ayuda visual -p. ej. el diagrama que explica los umbrales de Configuracion de
Ferlo-. No modal a proposito: a diferencia de los dialogos de edicion de la
app (todos abiertos con `.exec()`), esta se consulta mientras se sigue
editando la pagina de detras, asi que se abre con `.show()`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from src.shared.assets.resources import FERLO_VARIABLES_DIAGRAM
from src.shared.ui.components.app_button import AppButton


class DiagramViewerDialog(QDialog):
    def __init__(
        self,
        parent=None,
        image_path: Path = FERLO_VARIABLES_DIAGRAM,
        title: str = "Diagrama de variables",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 700)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setWidget(self._build_content(image_path))

        close_button = AppButton("Cerrar")
        close_button.clicked.connect(self.close)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addLayout(button_row)

    def _build_content(self, image_path: Path) -> QWidget:
        if not image_path.exists():
            return self._placeholder(image_path)

        if image_path.suffix.lower() == ".svg":
            widget = QSvgWidget(str(image_path))
            if not widget.renderer().isValid():
                return self._placeholder(image_path)
            return widget

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return self._placeholder(image_path)
        label = QLabel()
        label.setPixmap(pixmap)
        return label

    def _placeholder(self, image_path: Path) -> QWidget:
        label = QLabel(
            f"Diagrama no disponible todavía.\n\nColoca la imagen en:\n{image_path}"
        )
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
