from src.shared.assets.paths import (
    NAV_HOME,
    ACTION_SETTING,
    ACTION_DOCUMENT,
    ACTION_LIST
)

from src.shared.ui.components.tab_bar import TabBar


class FerloTabBar(TabBar):
    def __init__(self):
        super().__init__()

        self.add_item("Home", NAV_HOME)
        self.add_item("Data", ACTION_DOCUMENT )
        self.add_item("Configuración", ACTION_SETTING)
        self.add_item("Logs", ACTION_LIST)