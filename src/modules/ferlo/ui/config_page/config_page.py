"""Pestaña de Configuración de Ferlo (Fase 4, D7): a diferencia de
`src/modules/steriflow/ui/config_page/` -formulario escrito a mano-, aquí
cada sección y cada campo salen de `SETTINGS_SCHEMA`
(`logic/config.py`), así que añadir un umbral nuevo no toca este fichero.

Las rutas de entrada/archivo (D1) no están en el esquema de campos -son
carpetas, no números con rango- y se editan aparte, igual que Steriflow edita
sus rutas con un `QLineEdit` + "Seleccionar...".

La tabla de programas de consigna vive aquí también: no hay Excel de origen
que portar (ver `logic/analysis/programs.py`), así que se gestiona a mano.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from src.modules.ferlo.logic.config import Settings, save_settings
from src.modules.ferlo.logic.controller import FerloController
from src.modules.ferlo.logic.logs import agent_logger
from src.modules.ferlo.messages import catalog
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppButton, AppSaveButton
from src.shared.ui.components.diagram_viewer_dialog import DiagramViewerDialog

from src.modules.ferlo.ui.config_page.cycle_variables_group import CycleVariablesGroup
from src.modules.ferlo.ui.config_page.paths_group import PathsGroup
from src.modules.ferlo.ui.config_page.programs_group import ProgramsGroup
from src.modules.ferlo.ui.config_page.sections_grid import SectionsGrid


class FerloConfigPage(QWidget):
    def __init__(self, controller: FerloController):
        super().__init__()

        self._controller = controller
        self._draft = controller.settings.as_dict()
        self._dirty = False
        self._diagram_dialog: DiagramViewerDialog | None = None

        self._paths_group = PathsGroup(self._draft, self._mark_dirty)
        self._sections_grid = SectionsGrid(self._draft, self._mark_dirty)
        self._programs_group = ProgramsGroup(self._controller)
        self._cycle_variables_group = CycleVariablesGroup(self._draft, self._mark_dirty)

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_top_bar())
        layout.addWidget(self._paths_group)
        layout.addLayout(self._sections_grid)
        layout.addWidget(self._cycle_variables_group)
        layout.addWidget(self._programs_group)
        layout.addStretch()
        layout.addLayout(self._build_save_bar())

    # --- barra superior: ventana con el diagrama que explica las variables ---

    def _build_top_bar(self):
        diagram_button = AppButton("Ver diagrama de variables")
        diagram_button.clicked.connect(self._on_show_diagram)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(diagram_button)
        return row

    def _on_show_diagram(self):
        if self._diagram_dialog is None:
            self._diagram_dialog = DiagramViewerDialog(self)
        self._diagram_dialog.show()
        self._diagram_dialog.raise_()
        self._diagram_dialog.activateWindow()

    # --- guardado explícito: los cambios se acumulan en self._draft y no
    # tocan disco hasta que se pulsa "Guardar" ---

    def _build_save_bar(self):
        self._save_button = AppSaveButton("Guardar")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._on_save_clicked)

        discard_button = AppButton("Descartar cambios", color="#8a8a8a")
        discard_button.clicked.connect(self._on_discard_clicked)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(discard_button)
        row.addWidget(self._save_button)
        return row

    def _mark_dirty(self):
        self._dirty = True
        self._save_button.setEnabled(True)

    def _on_save_clicked(self):
        if self._draft == self._controller.settings.as_dict():
            push(Module.FERLO, catalog.config_unchanged())
            return

        settings = Settings(self._draft)
        save_settings(settings)
        self._controller.reload()
        self._dirty = False
        self._save_button.setEnabled(False)

        if settings.validation_warnings:
            push(Module.FERLO, catalog.config_out_of_range(settings.validation_warnings))
        else:
            announce(agent_logger(), catalog.config_saved())

    def _on_discard_clicked(self):
        self._draft.clear()
        self._draft.update(self._controller.settings.as_dict())
        self._paths_group.repaint()
        self._sections_grid.repaint()
        self._cycle_variables_group.repaint()
        self._dirty = False
        self._save_button.setEnabled(False)
