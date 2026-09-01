from src.ui.assets import (
    APP_ICON,
    MATERIA_RED_ICON,
    MATERIA_GREEN_ICON,
    MATERIA_YELLOW_ICON,
)
from src.ui.components.tab_bar import TabBar


class SteriflowTabBar(TabBar):
    def __init__(self):
        super().__init__()

        self.add_item("Home", APP_ICON)
        self.add_item("Configuración", MATERIA_RED_ICON)
        self.add_item("Data", MATERIA_RED_ICON)
        self.add_item("Logs", MATERIA_RED_ICON)
