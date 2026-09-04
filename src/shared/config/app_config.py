"""Configuración estática de la app (nombre, descripción...): lee
`appConfig/appConfig.yaml`, generado a partir de `appConfig.default.yaml` la
primera vez que se ejecuta (ver manager.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.config.manager import ensure_config_file, load_config

_MODULE = "app"


@dataclass(frozen=True)
class AppSettings:
    name: str
    description: str
    version: str
    language: str
    theme: str
    date_format: str
    time_format: str


def load_settings() -> AppSettings:
    ensure_config_file(_MODULE)
    raw = load_config(_MODULE)
    app = raw["app"]
    ui = raw["ui"]

    return AppSettings(
        name=app["name"],
        description=app["description"],
        version=app["version"],
        language=app["language"],
        theme=app["theme"],
        date_format=ui["dateFormat"],
        time_format=ui["timeFormat"],
    )
