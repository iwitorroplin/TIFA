from src.shared.paths import ASSETS_DIR

"""
extensiones: 
    - ico: solo para los iconos de la app
    - svg: formato por defecto
    - png: para imagenes grandes
"""

# file extensions
ICO_DIR = ASSETS_DIR / "ico"
SVG_DIR = ASSETS_DIR / "svg"
PNG_DIR = ASSETS_DIR / "png"

""""
ico: 
    - APP_ICON: icono general de la aplicación

"""

# ICO_DIR
APP_ICON = ICO_DIR / "app.ico"


"""
svg:
    - actions: acciones con iconos simples
    - navigation: elementos de navegacion
    - status: svg creados a mano con la forma de las materias de FF7
    - diagrams: creadas para explicar elementos complejos
    - characters: svg creados a mano con la silueta de los personajes de FF7 
    - app: reservago para el svg de la app mas detallado
"""

# SVG_DIR
SVG_ACTIONS_DIR = SVG_DIR / "actions"
SVG_NAVIGATION_DIR = SVG_DIR / "navigation"
SVG_STATUS_DIR = SVG_DIR / "status"
SVG_DIAGRAMS_DIR = SVG_DIR / "diagrams"
SVG_CHARACTERS_DIR = SVG_DIR / "characters"
SVG_APP = SVG_DIR / "app"

# SVG: ACTIONS
ACTION_ADD = SVG_ACTIONS_DIR / "add.svg"
ACTION_CHECK = SVG_ACTIONS_DIR / "check.svg"
ACTION_CROSS = SVG_ACTIONS_DIR / "cross.svg"
ACTION_DELETE = SVG_ACTIONS_DIR / "delete.svg"
ACTION_DOCUMENT = SVG_ACTIONS_DIR / "document.svg"
ACTION_EDIT = SVG_ACTIONS_DIR / "edit.svg"
ACTION_SAVE = SVG_ACTIONS_DIR / "save.svg"
ACTION_FOLDER = SVG_ACTIONS_DIR / "folder.svg"
ACTION_SETTING = SVG_ACTIONS_DIR / "settings.svg"
ACTION_USER = SVG_ACTIONS_DIR / "user.svg"
ACTION_START = SVG_ACTIONS_DIR / "start.svg"
ACTION_STOP = SVG_ACTIONS_DIR / "stop.svg"
ACTION_LIST = SVG_ACTIONS_DIR / "list.svg"
ACTION_DEFAULT = SVG_ACTIONS_DIR / "default.svg"



# SVG: DIAGRAMS
FERLO_VARIABLES_DIAGRAM = SVG_DIAGRAMS_DIR / "ferlo_variables.svg" # diagramas: una vez se limpie y quede correcto se pasara al formato png

# SVG: NAVIGATION
NAV_HOME = SVG_NAVIGATION_DIR / "home.svg"
NAV_UP = SVG_NAVIGATION_DIR / "arrow_up.svg"
NAV_DOWN = SVG_NAVIGATION_DIR / "arrow_down.svg"
NAV_RIGHT = SVG_NAVIGATION_DIR / "arrow_right.svg"
NAV_LEFT = SVG_NAVIGATION_DIR / "arrow_left.svg"
NAV_MODULE = SVG_NAVIGATION_DIR / "factory.svg"
NAV_EXIT = SVG_NAVIGATION_DIR / "exit.svg"

# SVG: STATUS
STATUS_GREY = SVG_STATUS_DIR / "materia_grey.svg"
STATUS_BLUE = SVG_STATUS_DIR / "materia_blue.svg"
STATUS_GREEN = SVG_STATUS_DIR / "materia_green.svg"
STATUS_PURPLE = SVG_STATUS_DIR / "materia_purple.svg"
STATUS_RED = SVG_STATUS_DIR / "materia_red.svg"
STATUS_YELLOW = SVG_STATUS_DIR / "materia_yellow.svg"

# SVG: CHARACTERS
CHARACTERS_TIFA = SVG_CHARACTERS_DIR / "tifa.svg"
CHARACTERS_CLOUD = SVG_CHARACTERS_DIR / "cloud.svg"
CHARACTERS_YUFI = SVG_CHARACTERS_DIR / "yufi.svg"
CHARACTERS_SEPHIROTH = SVG_CHARACTERS_DIR / "sephiroth.svg"

# SVG: APP
APP_LOGO = SVG_APP / "app_logo_v2.svg"

"""
png:
    - background: usado solo ne home
"""

# PNG
BACKGROUND_DIR = PNG_DIR / "background"
BACKGROUND_HOME = BACKGROUND_DIR / "midgar.png"
