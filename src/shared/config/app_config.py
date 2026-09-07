"""Configuración estática de la app (nombre, descripción...): lee
`appConfig/appConfig.yaml`, generado a partir de `appConfig.default.yaml` la
primera vez que se ejecuta (ver manager.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.config.manager import ensure_config_file, load_config, save_config

_MODULE = "app"

# El appConfig.yaml de una instalación anterior a esta opción no tiene la
# sección `logs`: se asume un año de historial en vez de petar al arrancar.
_DEFAULT_RETENTION_MONTHS = 12


@dataclass(frozen=True)
class AppSettings:
    name: str
    description: str
    version: str
    language: str
    theme: str
    date_format: str
    time_format: str
    # Meses de historial de log que se guardan; 0 = no borrar nunca.
    logs_retention_months: int


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
        logs_retention_months=raw.get("logs", {}).get(
            "retentionMonths", _DEFAULT_RETENTION_MONTHS
        ),
    )


def save_logs_retention_months(months: int) -> None:
    """Guarda solo ese campo, sobre el YAML tal cual está en disco.

    No se reescribe el fichero entero desde `AppSettings`: cualquier clave que
    el dataclass todavía no modele (añadida a mano, o de una versión más
    nueva) desaparecería en silencio al guardar.
    """
    ensure_config_file(_MODULE)
    raw = load_config(_MODULE)
    raw.setdefault("logs", {})["retentionMonths"] = months
    save_config(_MODULE, raw)
