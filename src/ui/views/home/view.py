from PySide6.QtGui import QPainter, QPixmap, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.config.app_config import load_settings as load_app_settings
from src.ui.assets import (
    MIDGAR_IMAGE,
    APP_LOGO,
    )


class HomeView(QWidget):
    """Cuadro de bienvenida de la app.

    Cuando esté terminada la app, este cuadro será reemplazado por el
    dashboard de la app. Solo un placeholder mientras tanto.
    """

    def __init__(self):
        super().__init__()

        app_settings = load_app_settings()

        # Fondo de Midgar. MIDGAR_IMAGE es un PNG ya rasterizado desde
        # Inkscape (ver assets.py): la versión vectorial tardaba segundos en
        # rasterizarse en cada resize. Se pinta en paintEvent en vez de con
        # un QLabel hermano: así el logo y los textos, al ser hijos de este
        # widget, se dibujan siempre encima sin depender de z-order ni de
        # atributos de transparencia.
        self._background = QPixmap(str(MIDGAR_IMAGE))

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo de la app, centrado en la vista. APP_LOGO es un SVG vectorial.
        image_logo = QLabel()
        image_logo.setPixmap(QPixmap(str(APP_LOGO)))
        image_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_logo)

        # label de bienvenida, centrado en la vista
        label_welcome = QLabel(f"Bienvenido a {app_settings.name}")
        label_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_welcome.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: white; text-shadow: 1px 1px 2px black;"
        )
        layout.addWidget(label_welcome)

        # descripción + versión, debajo del nombre
        label_description = QLabel(f"{app_settings.description} · v{app_settings.version}")
        label_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_description.setStyleSheet(
            "font-size: 14px; color: white; text-shadow: 1px 1px 2px black;"
        )
        layout.addWidget(label_description)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._background)
        super().paintEvent(event)
