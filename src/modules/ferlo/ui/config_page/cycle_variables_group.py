"""Grupo "Variables de deteccion de ciclo": abre el editor visual
(`CycleVariablesDialog`) donde viven las secciones `cycle_detection`,
`sterilization_phase`, `acceptance` y `review` de `SETTINGS_SCHEMA` -movidas
aquí desde `SectionsGrid` para verlas sobre la curva de un ciclo en vez de
como spinboxes sueltos.
"""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.modules.ferlo.ui.config_page.cycle_variables_dialog import CycleVariablesDialog
from src.shared.ui.components.app_button import AppButton


class CycleVariablesGroup(QGroupBox):
    def __init__(self, draft: dict, on_change, parent: QWidget | None = None):
        super().__init__("Variables de deteccion de ciclo", parent)
        self._draft = draft
        self._on_change = on_change
        self._dialog: CycleVariablesDialog | None = None

        hint = QLabel(
            "Umbrales de detección, esterilización, aceptación y revisión, vistos "
            "sobre la curva de un ciclo."
        )
        hint.setWordWrap(True)

        open_button = AppButton("Ver variables")
        open_button.clicked.connect(self._on_open_clicked)

        button_row = QHBoxLayout()
        button_row.addWidget(open_button)
        button_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(button_row)

    def _on_open_clicked(self) -> None:
        # Se recrea cada vez: los spinboxes deben partir siempre del draft
        # actual, no de un estado de una apertura anterior del modal.
        self._dialog = CycleVariablesDialog(self._draft, self._on_change, self)
        self._dialog.exec()

    def repaint(self):
        if self._dialog is not None and self._dialog.isVisible():
            self._dialog.close()
