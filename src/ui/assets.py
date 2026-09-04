from pathlib import Path

# path to the project root directory

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ICONS_DIR = _PROJECT_ROOT / "assets" / "icons"
_IMAGES_DIR = _PROJECT_ROOT / "assets" / "images"

# ICONOS .ico

# all icon are the same for now, but they can be changed in the future

APP_ICON = _ICONS_DIR / "app.ico"
WINDOW_ICON = _ICONS_DIR / "window.ico"
TRAY_ICON = _ICONS_DIR / "tray.ico"
UI_ICON = _ICONS_DIR / "ui.ico"

# IMGENES .svg

# LOGO

APP_LOGO = _IMAGES_DIR / "app_logo.svg"

# caracters
TIFA = _IMAGES_DIR / "caracters" / "tifa.svg"
CLOUD = _IMAGES_DIR / "caracters" / "cloud.svg"
SEPHIROTH = _IMAGES_DIR / "caracters" / "sephiroth.svg"
YUFI = _IMAGES_DIR / "caracters" / "yufi.svg"

# materias
# materia_colors
MATERIA_GREY_IMAGE = _IMAGES_DIR / "materias" / "materia_grey.svg"
MATERIA_BLUE_IMAGE = _IMAGES_DIR / "materias" / "materia_blue.svg"
MATERIA_GREEN_IMAGE = _IMAGES_DIR / "materias" / "materia_green.svg"
MATERIA_PURPLE_IMAGE = _IMAGES_DIR / "materias" / "materia_purple.svg"
MATERIA_RED_IMAGE = _IMAGES_DIR / "materias" / "materia_red.svg"
MATERIA_YELLOW_IMAGE = _IMAGES_DIR / "materias" / "materia_yellow.svg"
# materia_action
MATERIA_STARTER_IMAGE = _IMAGES_DIR / "materias" / "materia_start.svg"
MATERIA_STOP_IMAGE = _IMAGES_DIR / "materias" / "materia_stop.svg"

# OTHER
FOLDER_IMAGE = _IMAGES_DIR / "others" / "folder.svg"

# BACKGROUND
BACKGROUND_IMAGE = _IMAGES_DIR / "background" / "background.svg"
# .png y no .svg: el original vectorizado tardaba segundos en rasterizarse
# en cada resize (ver historial de home/view.py); exportado una vez desde
# Inkscape a 1920x1080, cargarlo es solo decodificar un PNG.
MIDGAR_IMAGE = _IMAGES_DIR / "background" / "midgar.png"