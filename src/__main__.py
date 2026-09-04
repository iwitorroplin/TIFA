import sys
import ctypes

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src.modules.registry import MODULES
from src.shared.db.schema import register_schema
from src.shared.assets.resources import APP_ICON 

from src.app.tray_app import TrayApp
from src.app.window_app import MainWindow


def _bootstrap() -> None:
    for spec in MODULES:
        if spec.ensure_tables is not None:
            register_schema(spec.ensure_tables)


def main():
    _bootstrap()

    if sys.platform == "win32":
        # Corriendo como script, Windows agrupa el proceso bajo python.exe
        # y usa su icono en la barra de tareas en vez del de la app, sin
        # importar lo que le pongamos con setWindowIcon. Un AppUserModelID
        # propio saca al proceso de ese grupo.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "tifa.app.1"
        )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    # Icono global de la aplicación
    app.setWindowIcon(QIcon(str(APP_ICON)))

    # Icono de la ventana principal
    window = MainWindow()
    tray = TrayApp(window)
    tray.show()
    window.show()


    sys.exit(app.exec())
