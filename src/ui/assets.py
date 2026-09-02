from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ICONS_DIR = _PROJECT_ROOT / "assets" / "icons"
_IMAGES_DIR = _PROJECT_ROOT / "assets" / "images"


# ICONOS .ico
# app
APP_ICON = _ICONS_DIR / "app.ico"
WINDOW_ICON = _ICONS_DIR / "window.ico"
TRAY_ICON = _ICONS_DIR / "tray.ico"
UI_ICON = _IMAGES_DIR / "ui.ico"

# materia

MATERIA_BLUE_ICON = _ICONS_DIR / "materia_blue.ico"
MATERIA_GREEN_ICON = _ICONS_DIR / "materia_green.ico"
MATERIA_PURPLE_ICON = _ICONS_DIR / "materia_purple.ico"
MATERIA_RED_ICON = _ICONS_DIR / "materia_red.ico"
MATERIA_YELLOW_ICON = _ICONS_DIR / "materia_yellow.ico"


# IMGENES .svg
APP_LOGO = _IMAGES_DIR / "app_logo.svg"
# personajes
TIFA = _IMAGES_DIR / "npcs" / "tifa.svg"
CLOUD = _IMAGES_DIR / "npcs" / "cloud.svg"
SEPHIROTH = _IMAGES_DIR / "npcs" / "sephiroth.svg"

# materias
MATERIA_GREY_IMAGE = _IMAGES_DIR / "materias" / "materia_grey.svg"
MATERIA_BLUE_IMAGE = _IMAGES_DIR / "materias" / "materia_blue.svg"
MATERIA_GREEN_IMAGE = _IMAGES_DIR / "materias" / "materia_green.svg"
MATERIA_PURPLE_IMAGE = _IMAGES_DIR / "materias" / "materia_purple.svg"
MATERIA_RED_IMAGE = _IMAGES_DIR / "materias" / "materia_red.svg"
MATERIA_YELLOW_IMAGE = _IMAGES_DIR / "materias" / "materia_yellow.svg"
