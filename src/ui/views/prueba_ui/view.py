from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.components.app_button import AppButton
from src.ui.components.loading_bar import LoadingBar
from src.ui.components.loading_dialog import LoadingDialog

from src.ui.assets import (
    APP_ICON,
    APP_LOGO,
    TIFA,
    CLOUD,
    SEPHIROTH,
    MATERIA_BLUE_IMAGE,
    MATERIA_GREEN_IMAGE,
    MATERIA_PURPLE_IMAGE,
    MATERIA_RED_IMAGE,
    MATERIA_YELLOW_IMAGE,
    MATERIA_BLUE_ICON,
    MATERIA_GREEN_ICON,
    MATERIA_PURPLE_ICON,
    MATERIA_RED_ICON,
    MATERIA_YELLOW_ICON,
)

_PROGRESS_TICK_MS = 150

_MATERIA_IMAGES = [
    MATERIA_BLUE_IMAGE,
    MATERIA_GREEN_IMAGE,
    MATERIA_PURPLE_IMAGE,
    MATERIA_RED_IMAGE,
    MATERIA_YELLOW_IMAGE,
]


class PruebaUIView(QWidget):
    """
    Sandbox visual para probar componentes de UI sueltos. 
    """

    def __init__(self):
        super().__init__()

        self._progress_value = 0

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(_PROGRESS_TICK_MS)
        self._progress_timer.timeout.connect(self._advance_progress)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_loading_bar_group())
        layout.addWidget(self._build_loading_dialog_group())
        layout.addWidget(self._build_images_group())
        layout.addWidget(self._build_icons_group())
        layout.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        self._progress_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._progress_timer.stop()

    def _build_loading_bar_group(self):
        group = QGroupBox("Barra de carga")

        indeterminate_bar = LoadingBar()
        indeterminate_bar.set_indeterminate()

        self._progress_bar = LoadingBar()
        self._progress_bar.set_progress(self._progress_value)

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(QLabel("Indeterminada:"))
        group_layout.addWidget(indeterminate_bar)
        group_layout.addWidget(QLabel("Con avance (bucle de prueba):"))
        group_layout.addWidget(self._progress_bar)

        return group

    def _advance_progress(self):
        self._progress_value = (self._progress_value + 2) % 101
        self._progress_bar.set_progress(self._progress_value)

    def _build_loading_dialog_group(self):
        group = QGroupBox("Ventana modal de carga")

        show_button = AppButton("Mostrar modal (3 s)")
        show_button.clicked.connect(self._show_loading_dialog)

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(show_button)

        return group

    def _show_loading_dialog(self):
        dialog = LoadingDialog(self, "Simulando una operación larga...")
        QTimer.singleShot(3000, dialog.accept)
        dialog.exec()

    def _build_images_group(self):
        group = QGroupBox("Imágenes SVG de prueba")

        images = [APP_LOGO, TIFA, CLOUD, SEPHIROTH, *_MATERIA_IMAGES]

        row_layout = QHBoxLayout(group)
        for image_path in images:
            image_widget = QSvgWidget(str(image_path))
            image_widget.setFixedSize(64, 64)
            row_layout.addWidget(image_widget)
        row_layout.addStretch()

        return group

    def _build_icons_group(self):
        group = QGroupBox("Iconos de prueba (.ico)")

        icons = [
            APP_ICON,
            MATERIA_BLUE_ICON,
            MATERIA_GREEN_ICON,
            MATERIA_PURPLE_ICON,
            MATERIA_RED_ICON,
            MATERIA_YELLOW_ICON,
        ]

        row_layout = QHBoxLayout(group)
        for icon_path in icons:
            icon_label = QLabel()
            # Las constantes de assets.py son rutas (Path), no QIcon: hay que
            # envolverlas para poder pedirles un pixmap, igual que ya hace
            # NavButton al construirse su propio QIcon a partir de la ruta.
            icon_label.setPixmap(QIcon(str(icon_path)).pixmap(32, 32))
            row_layout.addWidget(icon_label)
        row_layout.addStretch()

        return group



