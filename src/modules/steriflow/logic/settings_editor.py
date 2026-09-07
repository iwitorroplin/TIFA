"""Validación y guardado de la configuración editada en la pestaña
Configuración. Por ahora solo los enums de qué puede fallar -los usa
`messages/catalog.py` para redactar el aviso-; `SettingsDraft`, `validate` y
`apply` llegan cuando se extraiga `_persist()` de `ui/config_page.py`.
"""

from __future__ import annotations

from enum import Enum


class SettingsIssue(Enum):
    LOCAL_ROOT_REQUIRED = "local_root_required"
    SERVER_ROOT_REQUIRED = "server_root_required"
    AT_LEAST_ONE_SCHEDULE = "at_least_one_schedule"


class AutoclaveIssue(Enum):
    SOURCE_FOLDER_REQUIRED = "source_folder_required"
    LOCAL_FOLDER_REQUIRED = "local_folder_required"
    BACKUP_FOLDER_REQUIRED = "backup_folder_required"
