from __future__ import annotations

from typing import Any

from src.shared.config.loader import load_yaml
from src.shared.config.paths import config_path, default_config_path
from src.shared.config.writer import save_yaml


def ensure_config_file(module: str) -> bool:
    """Crea `appConfig/<modulo>Config.yaml` a partir de
    `appConfigDefault/<modulo>Config.default.yaml` si todavía no existe
    (primer arranque, o si alguien borró el archivo). Devuelve True solo si
    lo tuvo que crear."""
    path = config_path(module)
    if path.exists():
        return False

    default_path = default_config_path(module)
    if not default_path.exists():
        raise FileNotFoundError(
            f"No hay configuración en '{path}' ni configuración inicial en '{default_path}'."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    save_yaml(path, load_yaml(default_path))
    return True


def load_config(module: str) -> dict[str, Any]:
    return load_yaml(config_path(module))


def save_config(module: str, data: dict[str, Any]) -> None:
    save_yaml(config_path(module), data)


def restore_defaults(module: str) -> dict[str, Any]:
    """Descarta `appConfig/<modulo>Config.yaml` y lo vuelve a crear desde el
    default. Devuelve la configuración restaurada."""
    data = load_yaml(default_config_path(module))
    save_yaml(config_path(module), data)
    return data
