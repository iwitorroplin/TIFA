"""Configuración de la lógica de backup de Steriflow: lee y escribe el bloque
`steriflow:` de `config/machines.yaml`.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any

import yaml

# src/logic/steriflow/config.py -> parents[3] es la raíz del repo.
APP_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = APP_ROOT / "config"

CONFIG_FILENAME = "machines.yaml"
DEFAULT_CONFIG_FILENAME = "machines.default.yaml"


def resolve_path(value: str) -> Path:
    """Si la ruta viene en absoluto (o UNC) se respeta tal cual; si viene en
    relativo, se resuelve contra la carpeta del propio programa (útil para los
    valores por defecto, antes de que alguien la edite desde la pestaña de
    configuración con una ruta real)."""
    path = Path(value)
    return path if path.is_absolute() else APP_ROOT / path


def _load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _dump_yaml(filename: str, data: dict[str, Any]) -> None:
    path = CONFIG_DIR / filename
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def ensure_config_file() -> bool:
    """Crea machines.yaml a partir de machines.default.yaml si todavía no existe
    (primer arranque, o si alguien borró el archivo). Devuelve True solo si lo
    tuvo que crear."""
    path = CONFIG_DIR / CONFIG_FILENAME
    if path.exists():
        return False

    default_path = CONFIG_DIR / DEFAULT_CONFIG_FILENAME
    if not default_path.exists():
        raise FileNotFoundError(
            f"No hay configuración en '{path}' ni configuración inicial en '{default_path}'."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(default_path, path)
    return True


@dataclass(frozen=True)
class AutoclaveConfig:
    name: str
    ip: str
    active: bool


@dataclass(frozen=True)
class SteriflowPaths:
    local_root: Path
    server_root: Path
    logs_root: Path


@dataclass(frozen=True)
class ScheduleConfig:
    execution_hours: list[time]


@dataclass(frozen=True)
class SteriflowSettings:
    paths: SteriflowPaths
    autoclaves: list[AutoclaveConfig]
    schedule: ScheduleConfig


def load_settings() -> SteriflowSettings:
    raw = _load_yaml(CONFIG_FILENAME)["steriflow"]

    return SteriflowSettings(
        paths=SteriflowPaths(
            local_root=resolve_path(raw["local_root"]),
            server_root=resolve_path(raw["server_root"]),
            logs_root=resolve_path(raw["logs_root"]),
        ),
        autoclaves=[
            AutoclaveConfig(name=item["name"], ip=item["ip"], active=item["active"])
            for item in raw["autoclaves"]
        ],
        schedule=ScheduleConfig(
            execution_hours=sorted(
                time.fromisoformat(hour) for hour in raw["execution_hours"]
            )
        ),
    )


def save_settings(settings: SteriflowSettings) -> None:
    # Lee-modifica-escribe el archivo completo: así un futuro bloque ferlo:/macona:
    # en el mismo machines.yaml sobrevive a un Guardar hecho desde Steriflow.
    raw = _load_yaml(CONFIG_FILENAME) if (CONFIG_DIR / CONFIG_FILENAME).exists() else {}

    raw["steriflow"] = {
        "local_root": str(settings.paths.local_root),
        "server_root": str(settings.paths.server_root),
        "logs_root": str(settings.paths.logs_root),
        "execution_hours": [
            hour.strftime("%H:%M") for hour in settings.schedule.execution_hours
        ],
        "autoclaves": [
            {"name": a.name, "ip": a.ip, "active": a.active} for a in settings.autoclaves
        ],
    }

    _dump_yaml(CONFIG_FILENAME, raw)
