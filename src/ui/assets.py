from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _PROJECT_ROOT / "config" / "appConfig.yaml"

with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
    _icons = yaml.safe_load(f)["icons"]

APP_ICON = _PROJECT_ROOT / _icons["app"]
WINDOW_ICON = _PROJECT_ROOT / _icons["window"]
TRAY_ICON = _PROJECT_ROOT / _icons["tray"]
UI_ICON = _PROJECT_ROOT / _icons["ui"]
