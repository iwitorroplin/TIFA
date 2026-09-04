from src.ui.assets import APP_ICON
from src.ui.components.tab_bar import TabBar


class SteriflowTabBar(TabBar):
    def __init__(self):
        super().__init__()

        self.add_item("Home", APP_ICON, color="#3f51b5")
        self.add_item("Configuración")
        self.add_item("Data")
        self.add_item("Logs")
