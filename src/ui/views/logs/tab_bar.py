from src.shared.ui.components.tab_bar import TabBar


class LogsTabBar(TabBar):
    def __init__(self):
        super().__init__()

        self.add_item("Ferlo")
        self.add_item("Steriflow")
        self.add_item("Macona")
        self.add_item("Pasteurización")
