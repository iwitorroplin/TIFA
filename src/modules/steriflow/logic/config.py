"""Configuración de la lógica de backup de Steriflow: lee y escribe
`config/steriflowConfig.yaml`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from pathlib import Path

from src.shared.config.manager import ensure_config_file as _ensure_config_file
from src.shared.config.manager import load_config, save_config
from src.shared.paths import resolve_path

_MODULE = "steriflow"


def _default_path_folder(name: str) -> str:
    """Carpeta origen que se usaba antes de que fuera configurable.

    Apaño de migración: una instalación anterior a `path_folder` tiene su
    steriflowConfig.yaml sin esa clave, y `ensure_config_file` no reescribe un
    fichero que ya existe, así que la clave nunca llegaría sola desde el
    default. Se reproduce aquí la ruta que estaba hardcodeada en el backup
    para que esa instalación siga copiando igual que ayer. Se puede quitar
    cuando todas hayan guardado la configuración al menos una vez.
    """
    return fr"\\{name}\Export"


def _default_backup_folder(name: str, server_root: Path) -> str:
    """Carpeta de backup que se usaba antes de ser configurable por autoclave.

    Apaño de migración equivalente a `_default_path_folder`: antes de existir
    `backup_folder`, el destino de cada autoclave se calculaba solo como
    `server_root/<nombre>`. Se reproduce aquí para que una instalación antigua
    siga replicando exactamente en el mismo sitio hasta que guarde una vez.
    """
    return str(server_root / name)


def _default_local_folder(name: str, local_root: Path) -> str:
    """Carpeta local que se usaba antes de ser configurable por autoclave.

    Apaño de migración equivalente a `_default_backup_folder`: antes de existir
    `local_folder`, el staging de cada autoclave se calculaba solo como
    `local_root/<nombre>`. Se reproduce aquí para que una instalación antigua
    siga usando exactamente la misma carpeta hasta que guarde una vez.
    """
    return str(local_root / name)


@dataclass(frozen=True)
class AutoclaveConfig:
    name: str
    ip: str
    # Cadena y no Path en los tres campos de ruta: pasarlos por Path le añade
    # una barra final a un recurso pelado (\\MAQUINA\Export), reescribiendo en
    # silencio lo que escribió el usuario. Tampoco pasan por `resolve_path`,
    # que convertiría un valor vacío en la raíz del programa.
    #
    # path_folder: carpeta compartida (UNC) de la propia autoclave, de la que
    # se traen sus PDF. Recurso de red: si la máquina está apagada, no hay
    # señal y esta ruta no es alcanzable (ver src.modules.steriflow.logic.network.is_reachable).
    path_folder: str
    # local_folder: carpeta local de staging de esta autoclave en el PC donde
    # corre TIFA (destino del PASO 3, origen del PASO 5).
    local_folder: str
    # backup_folder: carpeta del servidor de almacenamiento a la que se
    # replica lo recogido en local_folder (PASO 5 del backup).
    backup_folder: str
    active: bool


@dataclass(frozen=True)
class SteriflowPaths:
    # local_root/server_root: carpetas raíz donde, por convención, vive la
    # subcarpeta de cada autoclave (local_root/<nombre>, server_root/<nombre>).
    # Cada autoclave puede apuntar su local_folder/backup_folder a otro sitio,
    # pero estas dos son las que abren los botones "Abrir Local"/"Abrir
    # Servidor" de la home page.
    local_root: Path
    server_root: Path


@dataclass(frozen=True)
class ScheduleConfig:
    execution_hours: list[time]


@dataclass(frozen=True)
class SteriflowSettings:
    paths: SteriflowPaths
    autoclaves: list[AutoclaveConfig]
    schedule: ScheduleConfig
    # Si el modo automático debe arrancar solo al abrir la app. Se guarda
    # aquí -y no solo en memoria en el controller- para que apagarlo desde la
    # home page sobreviva a un reinicio (ver SteriflowController.set_auto_enabled).
    auto_enabled: bool


def ensure_config_file() -> bool:
    return _ensure_config_file(_MODULE)


def load_settings() -> SteriflowSettings:
    raw = load_config(_MODULE)

    local_root = resolve_path(raw.get("local_root", "data/steriflow/local"))
    server_root = resolve_path(raw.get("server_root", "data/steriflow/server"))

    return SteriflowSettings(
        paths=SteriflowPaths(
            local_root=local_root,
            server_root=server_root,
        ),
        autoclaves=[
            AutoclaveConfig(
                name=item["name"],
                ip=item["ip"],
                path_folder=item.get("path_folder") or _default_path_folder(item["name"]),
                local_folder=item.get("local_folder")
                or _default_local_folder(item["name"], local_root),
                backup_folder=item.get("backup_folder")
                or _default_backup_folder(item["name"], server_root),
                active=item["active"],
            )
            for item in raw["autoclaves"]
        ],
        schedule=ScheduleConfig(
            execution_hours=sorted(
                time.fromisoformat(hour) for hour in raw["execution_hours"]
            )
        ),
        auto_enabled=bool(raw.get("auto_enabled", False)),
    )


def save_settings(settings: SteriflowSettings) -> None:
    save_config(_MODULE, {
        "local_root": str(settings.paths.local_root),
        "server_root": str(settings.paths.server_root),
        "execution_hours": [
            hour.strftime("%H:%M") for hour in settings.schedule.execution_hours
        ],
        "auto_enabled": settings.auto_enabled,
        "autoclaves": [
            {
                "name": a.name,
                "ip": a.ip,
                "path_folder": a.path_folder,
                "local_folder": a.local_folder,
                "backup_folder": a.backup_folder,
                "active": a.active,
            }
            for a in settings.autoclaves
        ],
    })
