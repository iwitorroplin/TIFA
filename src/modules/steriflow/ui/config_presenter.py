"""Estado de la pestaña de Configuración que no es un widget: el borrador en
edición (rutas, autoclaves, horarios) y el último estado de red conocido de
cada autoclave. Sin PySide6 -la página lo muta y se repinta desde él por un
único `_repaint()` propio (ver `SteriflowConfigPage`)-.

El checker de conectividad (`tasks/status_checker.py`) sí es Qt: se queda en
la página, que solo empuja aquí el resultado con `set_status()` cuando la
señal llega ya en el hilo de la interfaz. Este presenter nunca se toca desde
un hilo de trabajo (ver el docstring de `tasks/__init__.py`).
"""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from src.modules.steriflow.logic.config import AutoclaveConfig
from src.modules.steriflow.logic.network import MachineStatus
from src.modules.steriflow.logic.settings_editor import (
    SaveOutcome,
    SaveStatus,
    SettingsDraft,
    apply as apply_settings,
)

if TYPE_CHECKING:
    from src.modules.steriflow.logic.controller import SteriflowController


class SteriflowConfigPresenter:
    def __init__(self, controller: SteriflowController) -> None:
        self._controller = controller
        self._statuses: dict[str, MachineStatus] = {}
        self._draft = self._draft_from_settings()

    def load(self) -> None:
        """Descarta el borrador y lo reconstruye desde lo ya guardado
        (`controller.settings`). El estado de red anterior deja de ser de
        fiar -por eso también se vacía- y se recalcula desde fuera."""
        self._draft = self._draft_from_settings()
        self._statuses = {}

    def _draft_from_settings(self) -> SettingsDraft:
        settings = self._controller.settings
        return SettingsDraft(
            local_root_text=str(settings.paths.local_root),
            server_root_text=str(settings.paths.server_root),
            autoclaves=list(settings.autoclaves),
            execution_hours=list(settings.schedule.execution_hours),
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
        self._statuses.pop(autoclave.name, None)

    def update_autoclave(self, row: int, autoclave: AutoclaveConfig) -> None:
        # El nombre/IP puede haber cambiado: el estado de red anterior (del
        # nombre viejo, y del nuevo por si ya había uno) ya no es de fiar.
        old_name = self._draft.autoclaves[row].name
        self._draft.autoclaves[row] = autoclave
        self._statuses.pop(old_name, None)
        self._statuses.pop(autoclave.name, None)

    def remove_autoclave(self, row: int) -> None:
        removed = self._draft.autoclaves.pop(row)
        self._statuses.pop(removed.name, None)

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

    # --- guardado ---

    def save(self) -> SaveOutcome:
        outcome = apply_settings(self._controller, self._draft)
        if outcome.status is SaveStatus.SAVED:
            # Resincroniza con lo que quedó realmente en disco (rutas
            # resueltas, horas ordenadas...) en vez de dejar el borrador tal
            # y como lo escribió el usuario.
            self.load()
        return outcome

    # --- estado de red ---

    def status_targets(self) -> list[tuple[str, str]]:
        return [(autoclave.name, autoclave.ip) for autoclave in self._draft.autoclaves]

    def set_status(self, name: str, status: MachineStatus) -> None:
        self._statuses[name] = status

    def status_of(self, name: str) -> MachineStatus | None:
        return self._statuses.get(name)
