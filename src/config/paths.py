# RUTAS DE CONFIGURACIÓN

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"

DEFAULT_CONFIG_DIR = CONFIG_DIR / "appConfigDefault"
APP_CONFIG_DIR = CONFIG_DIR / "appConfig"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path