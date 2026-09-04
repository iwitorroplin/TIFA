from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from src.shared.assets.resources import TRAY_ICON


class TrayApp(QSystemTrayIcon):
    def __init__(self, window):
        super().__init__(QIcon(str(TRAY_ICON)))
        self._window = window
        self.setToolTip("TIFA")

        menu = QMenu()

        show_action = QAction("Mostrar ventana", menu)
        show_action.triggered.connect(self._window.show)
        menu.addAction(show_action)

        quit_action = QAction("Salir", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._window.show()

