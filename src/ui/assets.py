from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ICONS_DIR = _PROJECT_ROOT / "assets" / "icons"
_IMAGES_DIR = _PROJECT_ROOT / "assets" / "images"

APP_ICON = _ICONS_DIR / "app.ico"
WINDOW_ICON = _ICONS_DIR / "window.ico"
TRAY_ICON = _ICONS_DIR / "tray.ico"
UI_ICON = _IMAGES_DIR / "tifa.svg"

MATERIA_BLUE_ICON = _ICONS_DIR / "materia_blue.ico"
MATERIA_GREEN_ICON = _ICONS_DIR / "materia_green.ico"
MATERIA_PURPLE_ICON = _ICONS_DIR / "materia_purple.ico"
MATERIA_RED_ICON = _ICONS_DIR / "materia_red.ico"
MATERIA_YELLOW_ICON = _ICONS_DIR / "materia_yellow.ico"
