import sys

from PySide6.QtWidgets import QApplication

from src.modules.registry import MODULES
from src.shared.db.schema import register_schema
from src.ui.tray_app import TrayApp
from src.ui.window_app import MainWindow


def _bootstrap() -> None:
    for spec in MODULES:
        if spec.ensure_tables is not None:
            register_schema(spec.ensure_tables)


def main():
    _bootstrap()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    tray = TrayApp(window)
    tray.show()
    window.show()


    sys.exit(app.exec())
