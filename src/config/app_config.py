"""Configuración estática de la app (nombre, descripción...): lee
`config/appConfig.yaml`. A diferencia de Ferlo/Steriflow/Macona/Pasteurización
(ver files.py), no tiene `.default.yaml` ni edición desde la interfaz: viene
ya versionada con el repo, así que solo hace falta leerla.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config.files import load_config

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
