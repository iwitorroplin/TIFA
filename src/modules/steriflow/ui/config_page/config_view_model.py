"""View model de la pestaña de Configuración: el borrador en edición (rutas,
autoclaves, horarios, columnas). Sin PySide6 -la página lo muta y se repinta
desde él por un único `_repaint()` propio (ver `SteriflowConfigPage`)-.

El estado de red de cada autoclave ya no vive aquí: se muestra y se
comprueba desde el groupbox de estado de la home page.
"""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from src.modules.steriflow.logic.config import AutoclaveConfig
from src.modules.steriflow.logic.settings_editor import (
    SaveOutcome,
    SaveStatus,
    SettingsDraft,
    apply as apply_settings,
)
from src.modules.steriflow.logic.sterilization.columns import CYCLE_COLUMNS, CycleColumn

if TYPE_CHECKING:
    from src.modules.steriflow.logic.controller import SteriflowController


class SteriflowConfigViewModel:
    def __init__(self, controller: SteriflowController) -> None:
        self._controller = controller
        self._draft = self._draft_from_settings()

    def load(self) -> None:
        """Descarta el borrador y lo reconstruye desde lo ya guardado
        (`controller.settings`)."""
        self._draft = self._draft_from_settings()

    def _draft_from_settings(self) -> SettingsDraft:
        settings = self._controller.settings
        return SettingsDraft(
            local_root_text=str(settings.paths.local_root),
            server_root_text=str(settings.paths.server_root),
            autoclaves=list(settings.autoclaves),
            execution_hours=list(settings.schedule.execution_hours),
            visible_column_keys=set(settings.columns.visible_keys),
        )

    # --- rutas ---

    def local_root(self) -> str:
        return self._draft.local_root_text

    def server_root(self) -> str:
        return self._draft.server_root_text

    def set_local_root(self, text: str) -> None:
        self._draft.local_root_text = text

    def set_server_root(self, text: str) -> None:
        self._draft.server_root_text = text

    # --- autoclaves ---

    def autoclaves(self) -> list[AutoclaveConfig]:
        return self._draft.autoclaves

    def add_autoclave(self, autoclave: AutoclaveConfig) -> None:
        self._draft.autoclaves.append(autoclave)

    def update_autoclave(self, row: int, autoclave: AutoclaveConfig) -> None:
        self._draft.autoclaves[row] = autoclave

    def remove_autoclave(self, row: int) -> None:
        del self._draft.autoclaves[row]

    # --- horarios ---

    def hours(self) -> list[time]:
        return self._draft.execution_hours

    def add_hour(self, value: time) -> None:
        self._draft.execution_hours.append(value)

    def update_hour(self, row: int, value: time) -> None:
        self._draft.execution_hours[row] = value

    def remove_hour(self, row: int) -> None:
        del self._draft.execution_hours[row]

    def can_remove_hour(self) -> bool:
        return len(self._draft.execution_hours) > 1

    # --- columnas ---

    def configurable_columns(self) -> list[CycleColumn]:
        """Las columnas que se pueden apagar (las fijas no se preguntan)."""
        return [col for col in CYCLE_COLUMNS if not col.fixed]

    def is_column_visible(self, key: str) -> bool:
        return key in self._draft.visible_column_keys

    def set_column_visible(self, key: str, visible: bool) -> None:
        if visible:
            self._draft.visible_column_keys.add(key)
        else:
            self._draft.visible_column_keys.discard(key)

    # --- guardado ---

    def save(self) -> SaveOutcome:
        outcome = apply_settings(self._controller, self._draft)
        if outcome.status is SaveStatus.SAVED:
            # Resincroniza con lo que quedó realmente en disco (rutas
            # resueltas, horas ordenadas...) en vez de dejar el borrador tal
            # y como lo escribió el usuario.
            self.load()
        return outcome
