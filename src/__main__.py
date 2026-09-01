import sys

from PySide6.QtWidgets import QApplication

from src.ui.tray_app import TrayApp
from src.ui.window_app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    tray = TrayApp(window)
    tray.show()

    sys.exit(app.exec())
