from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QPushButton, QToolButton

from src.shared.assets.resources import (
    FOLDER_IMAGE,
    MATERIA_STARTER_IMAGE,
    MATERIA_STOP_IMAGE
)

from src.shared.messages.types import MessageType
from src.shared.utils.folders import open_folder


def _button_colors(color):
    base = QColor(color)
    return base.name(), base.lighter(130).name(), base.darker(120).name()


class AppButton(QPushButton):
    def __init__(self, text, color="#4d88cb"):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        default, hover, pressed = _button_colors(color)

        self.setStyleSheet(
            f"""
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                background-color: {default};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
            """
        )


class _AppIconButton(QToolButton):
    """Boton con icono grande y texto debajo. Las subclases fijan _icon_path."""

    _icon_path = None

    def __init__(self, text, color="#4d88cb"):
        super().__init__()
        self.setText(text)
        self.setIcon(QIcon(str(self._icon_path)))
        self.setIconSize(QSize(48, 48))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        default, hover, pressed = _button_colors(color)

        self.setStyleSheet(
            f"""
            QToolButton {{
                border: none;
                border-radius: 6px;
                padding: 10px 14px;
                background-color: {default};
                color: white;
            }}
            QToolButton:hover {{
                background-color: {hover};
            }}
            QToolButton:pressed {{
                background-color: {pressed};
            }}
            """
        )


class AppFolderButton(_AppIconButton):
    """Boton con icono de carpeta. Abre `path` al pulsarlo."""

    _icon_path = FOLDER_IMAGE

    def __init__(self, text, path, logger, create=False, color="#4d88cb"):
        super().__init__(text, color)
        self._path = path
        self._logger = logger
        self._create = create
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        # `open_folder` ya deja el motivo en el log; esta línea es la que ve el
        # usuario. Una carpeta de servidor que no abre suele ser la red caida,
        # que es justo lo que conviene saber antes del próximo backup.
        if not open_folder(self._path, self._logger, create=self._create):
            self._logger.log(
                f"No se pudo abrir la carpeta: {self._path}", talk=MessageType.WARNING
            )


class AppStartButton(_AppIconButton):
    # boton con icono de materia start, para acciones de backup
    _icon_path = MATERIA_STARTER_IMAGE


class AppStopButton(_AppIconButton):
    # boton con icono de materia stop, para detener el backup
    _icon_path = MATERIA_STOP_IMAGE

    def __init__(self, text, color="#e20c0c"):
        super().__init__(text, color)
