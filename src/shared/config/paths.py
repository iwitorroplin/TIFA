from pathlib import Path

from src.shared.paths import CONFIG_DIR

APP_CONFIG_DIR = CONFIG_DIR / "appConfig"
DEFAULT_CONFIG_DIR = CONFIG_DIR / "appConfigDefault"


def config_path(module: str) -> Path:
    return APP_CONFIG_DIR / f"{module}Config.yaml"


def default_config_path(module: str) -> Path:
    return DEFAULT_CONFIG_DIR / f"{module}Config.default.yaml"
