"""Validación y guardado de la configuración editada en la pestaña
Configuración: lo que antes amontonaba `_persist()` en `ui/config_page.py`
-validar campos obligatorios, construir el modelo de dominio desde el
borrador, compararlo con lo ya guardado y persistir si hace falta-.

No avisa al usuario: eso es cosa de quien llama (`ui/config_page.py`), a
partir del `SaveOutcome`/`SettingsIssue`/`AutoclaveIssue` que devuelve este
módulo -ver `messages/catalog.py`, que redacta el texto de cada uno-. Este
módulo no importa el catálogo a propósito: es al revés (`catalog.py` importa
estos enums), y las dos direcciones a la vez serían un ciclo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from src.modules.steriflow.logic.config import (
    AutoclaveConfig,
    ScheduleConfig,
    SteriflowPaths,
    SteriflowSettings,
    save_settings,
)

if TYPE_CHECKING:
    # No en tiempo de ejecución: controller.py importa (a través de
    # backup/scheduler.py) messages/catalog.py, que importa los enums de
    # este fichero -un import real aquí cerraría un ciclo-. `apply()` solo
    # necesita el tipo para el type checker; en runtime recibe el objeto ya
    # construido, sin necesidad de importar la clase.
    from src.modules.steriflow.logic.controller import SteriflowController


class SettingsIssue(Enum):
    LOCAL_ROOT_REQUIRED = "local_root_required"
    SERVER_ROOT_REQUIRED = "server_root_required"
    AT_LEAST_ONE_SCHEDULE = "at_least_one_schedule"


class AutoclaveIssue(Enum):
    SOURCE_FOLDER_REQUIRED = "source_folder_required"
    LOCAL_FOLDER_REQUIRED = "local_folder_required"
    BACKUP_FOLDER_REQUIRED = "backup_folder_required"


@dataclass
class SettingsDraft:
    local_root_text: str
    server_root_text: str
    autoclaves: list[AutoclaveConfig]
    execution_hours: list[time]

    def to_settings(self, *, auto_enabled: bool) -> SteriflowSettings:
        return SteriflowSettings(
            paths=SteriflowPaths(
                local_root=Path(self.local_root_text),
                server_root=Path(self.server_root_text),
            ),
            autoclaves=self.autoclaves,
            # sorted(): load_settings() también ordena las horas al leer el
            # yaml. Sin esto, dos listas con las mismas horas en otro orden
            # se verían "distintas" en el dirty-check de apply() y el
            # guardado entraría en bucle cada vez que se abre esta pestaña.
            schedule=ScheduleConfig(execution_hours=sorted(self.execution_hours)),
            auto_enabled=auto_enabled,
        )


class SaveStatus(Enum):
    SAVED = "saved"
    UNCHANGED = "unchanged"
    INVALID = "invalid"


@dataclass(frozen=True)
class SaveOutcome:
    status: SaveStatus
    issue: SettingsIssue | None = None


def validate(draft: SettingsDraft) -> SettingsIssue | None:
    """None si el borrador está completo. El orden importa: con dos campos
    mal a la vez, decide cuál de los dos avisos ve el usuario primero."""
    if not draft.local_root_text.strip():
        return SettingsIssue.LOCAL_ROOT_REQUIRED
    if not draft.server_root_text.strip():
        return SettingsIssue.SERVER_ROOT_REQUIRED
    if not draft.execution_hours:
        return SettingsIssue.AT_LEAST_ONE_SCHEDULE
    return None


def validate_autoclave(autoclave: AutoclaveConfig) -> AutoclaveIssue | None:
    if not autoclave.path_folder.strip():
        return AutoclaveIssue.SOURCE_FOLDER_REQUIRED
    if not autoclave.local_folder.strip():
        return AutoclaveIssue.LOCAL_FOLDER_REQUIRED
    if not autoclave.backup_folder.strip():
        return AutoclaveIssue.BACKUP_FOLDER_REQUIRED
    return None


def apply(controller: SteriflowController, draft: SettingsDraft) -> SaveOutcome:
    issue = validate(draft)
    if issue is not None:
        return SaveOutcome(SaveStatus.INVALID, issue)

    settings = draft.to_settings(auto_enabled=controller.settings.auto_enabled)

    # `editingFinished` salta cada vez que un campo pierde el foco, haya
    # cambiado o no: sin esta comparación, pasear por la página guardaba,
    # reiniciaba el scheduler y sacaba un "guardada" cada dos clics.
    if settings == controller.settings:
        return SaveOutcome(SaveStatus.UNCHANGED)

    save_settings(settings)
    controller.reload()
    return SaveOutcome(SaveStatus.SAVED)
