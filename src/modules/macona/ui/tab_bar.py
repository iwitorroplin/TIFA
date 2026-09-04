from src.shared.ui.components.tab_bar import TabBar


class MaconaTabBar(TabBar):
    def __init__(self):
        super().__init__()

        self.add_item("Tab 1")
        self.add_item("Tab 2")
