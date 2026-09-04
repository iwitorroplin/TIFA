from src.shared.assets.paths import (
    BACKGROUND_DIR,
    CHARACTERS_DIR,
    ICONS_DIR,
    IMAGES_DIR,
    MATERIAS_DIR,
    OTHERS_DIR,
)

# ICONOS .ico

# all icon are the same for now, but they can be changed in the future

APP_ICON = ICONS_DIR / "app.ico"
WINDOW_ICON = ICONS_DIR / "window.ico"
TRAY_ICON = ICONS_DIR / "tray.ico"
UI_ICON = ICONS_DIR / "ui.ico"

# IMGENES .svg

# LOGO

APP_LOGO = IMAGES_DIR / "app_logo.svg"
APP_LOGO_V2 = IMAGES_DIR / "app_logo_v2.svg"

# characters
TIFA = CHARACTERS_DIR / "tifa.svg"
CLOUD = CHARACTERS_DIR / "cloud.svg"
SEPHIROTH = CHARACTERS_DIR / "sephiroth.svg"
YUFI = CHARACTERS_DIR / "yufi.svg"

# materias
# materia_colors
MATERIA_GREY_IMAGE = MATERIAS_DIR / "materia_grey.svg"
MATERIA_BLUE_IMAGE = MATERIAS_DIR / "materia_blue.svg"
MATERIA_GREEN_IMAGE = MATERIAS_DIR / "materia_green.svg"
MATERIA_PURPLE_IMAGE = MATERIAS_DIR / "materia_purple.svg"
MATERIA_RED_IMAGE = MATERIAS_DIR / "materia_red.svg"
MATERIA_YELLOW_IMAGE = MATERIAS_DIR / "materia_yellow.svg"
# materia_action
MATERIA_STARTER_IMAGE = MATERIAS_DIR / "materia_start.svg"
MATERIA_STOP_IMAGE = MATERIAS_DIR / "materia_stop.svg"

# OTHER
FOLDER_IMAGE = OTHERS_DIR / "folder.svg"

# BACKGROUND
# .png y no .svg: el original vectorizado tardaba segundos en rasterizarse
# en cada resize (ver historial de home/view.py); exportado una vez desde
# Inkscape a 1920x1080, cargarlo es solo decodificar un PNG.
MIDGAR_IMAGE = BACKGROUND_DIR / "midgar.png"
