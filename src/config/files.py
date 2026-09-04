"""Carga y guardado de la configuración de cada módulo.

Ferlo, Steriflow, Macona y Pasteurización no comparten ni un solo campo de
configuración entre sí, así que cada uno tiene su propio YAML en vez de
compartir uno (a diferencia de la base de datos, donde sí conviene un único
fichero): `<modulo>Config.yaml` es el que edita la app y no se versiona -cada
instalación tiene rutas e IPs propias-, y `<modulo>Config.default.yaml` sí se
versiona y es el que se copia la primera vez que `<modulo>Config.yaml` todavía
no existe. Los cuatro módulos usan exactamente este mismo esquema de ficheros.
"""

from __future__ import annotations

import shutil
from typing import Any

import yaml

from src.config.paths import CONFIG_DIR


def _config_path(module: str):
    return CONFIG_DIR / f"{module}Config.yaml"


def _default_config_path(module: str):
    return CONFIG_DIR / f"{module}Config.default.yaml"


def ensure_config_file(module: str) -> bool:
    """Crea `<modulo>Config.yaml` a partir de `<modulo>Config.default.yaml` si
    todavía no existe (primer arranque, o si alguien borró el archivo).
    Devuelve True solo si lo tuvo que crear."""
    path = _config_path(module)
    if path.exists():
        return False

    default_path = _default_config_path(module)
    if not default_path.exists():
        raise FileNotFoundError(
            f"No hay configuración en '{path}' ni configuración inicial en '{default_path}'."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(default_path, path)
    return True


def load_config(module: str) -> dict[str, Any]:
    path = _config_path(module)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def save_config(module: str, data: dict[str, Any]) -> None:
    path = _config_path(module)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)
