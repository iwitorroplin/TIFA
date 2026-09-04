import sys

from PySide6.QtWidgets import QApplication

from src.logic.steriflow.schema import ensure_tables as _ensure_steriflow_tables
from src.shared.db.schema import register_schema
from src.ui.tray_app import TrayApp
from src.ui.window_app import MainWindow


def _bootstrap() -> None:
    # Registro explícito hasta que exista src/modules/registry.py (fase
    # siguiente del refactor), que lo generará automáticamente por módulo.
    register_schema(_ensure_steriflow_tables)


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
