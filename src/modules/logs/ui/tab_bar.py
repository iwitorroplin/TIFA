from src.shared.ui.components.tab_bar import TabBar


class LogsTabBar(TabBar):
    def __init__(self, labels):
        super().__init__()

        for label in labels:
            self.add_item(label)
