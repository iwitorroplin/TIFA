from src.shared.ui.components.tab_bar import TabBar


class FerloTabBar(TabBar):
    def __init__(self):
        super().__init__()

        self.add_item("Importación")
        self.add_item("Ciclos")
        self.add_item("Configuración")
