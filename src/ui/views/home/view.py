from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.ui.assets import (
    UI_ICON,
    TIFA,
    CLOUD,
    SEPHIROTH,
    )


class HomeView(QWidget):
    def __init__(self):
        super().__init__()

        """
        Cuadro de bienvenida de la app

        cuando este terminada la app, este cuadro sera reemplazado por el dashboard de la app

        title = QLabel("7th Heaven")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        image_ui = QSvgWidget(str(UI_ICON))
        image_ui.setFixedSize(160, 160)
        
        
        """


        # los añadimos en la esquina a la derecha de la ventana
        image_tifa = QSvgWidget(str(TIFA))
        image_tifa.setFixedSize(160, 160)
        image_cloud = QSvgWidget(str(CLOUD))
        image_cloud.setFixedSize(160, 160)
        image_sephiroth = QSvgWidget(str(SEPHIROTH))
        image_sephiroth.setFixedSize(160, 160)

        layout = QVBoxLayout(self)
        layout.addStretch()

        """
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_ui, alignment=Qt.AlignmentFlag.AlignCenter)
        """


        # los añadimos en la esquina a la derecha de la ventana
        # Solo como Placeholder hasta que la app este lista
        layout.addWidget(image_tifa, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(image_cloud, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(image_sephiroth, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()
