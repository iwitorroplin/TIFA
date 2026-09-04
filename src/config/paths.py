

"""
OLD PATHS FILE. DO NOT USE. THIS FILE IS KEPT FOR REFERENCE PURPOSES ONLY.

from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = APP_ROOT / "config"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else APP_ROOT / path

"""

# RUTAS DE CONFIGURACIÓN

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"

DEFAULT_CONFIG_DIR = CONFIG_DIR / "appConfigDefault"
APP_CONFIG_DIR = CONFIG_DIR / "appConfig"