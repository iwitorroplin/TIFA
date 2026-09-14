from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QPushButton, QToolButton

from src.shared.assets.paths import (
    ACTION_ADD,
    ACTION_CHECK,
    ACTION_CROSS,
    ACTION_DELETE,
    ACTION_EDIT,
    ACTION_FOLDER,
    ACTION_SAVE,
    ACTION_START,
    ACTION_STOP,
    ACTION_DEFAULT,
    STATUS_GREY,
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
        self.setIconSize(QSize(20, 20))
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

    _icon_path = ACTION_FOLDER

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
    # boton con icono
    _icon_path = ACTION_START

    def __init__(self, text="Guardar", color="#3fa34d"):
        super().__init__(text, color)


class AppStopButton(_AppIconButton):
    # boton con icono 
    _icon_path = ACTION_STOP

    def __init__(self, text, color="#e20c0c"):
        super().__init__(text, color)


class AppSaveButton(_AppIconButton):
    # boton de guardado
    _icon_path = ACTION_SAVE

    def __init__(self, text="Guardar", color="#3fa34d"):
        super().__init__(text, color)


class AppDeleteButton(_AppIconButton):
    # boton de eliminar
    _icon_path = ACTION_DELETE

    def __init__(self, text="Eliminar", color="#e20c0c"):
        super().__init__(text, color)


class AppModifyButton(_AppIconButton):
    # boton de modificar/editar
    _icon_path = ACTION_EDIT

    def __init__(self, text="Modificar", color="#4d88cb"):
        super().__init__(text, color)


class AppAddButton(_AppIconButton):
    # boton de anadir un elemento nuevo
    _icon_path = ACTION_ADD

    def __init__(self, text="Añadir", color="#4d88cb"):
        super().__init__(text, color)

class AppDefaultButton (_AppIconButton):
    # boton para volver a la configuracion default del modulo
    _icon_path = ACTION_DEFAULT

    def __init__(self, text="Default", color="#663781"):
        super().__init__(text, color)


class AppStatusButton(QToolButton):
    """Boton-chip con un icono de estado (materia) y el nombre debajo.

    Pensado para representar el estado de cada máquina de un grupo (p. ej.
    las autoclaves de Steriflow) con un vistazo, y a la vez servir de acción
    para volver a comprobar esa máquina en concreto. El icono se cambia en
    caliente con `set_icon()` según van llegando los resultados, sin
    reconstruir el botón.
    """

    def __init__(self, text, icon_path=STATUS_GREY, color="#3a3a3a"):
        super().__init__()
        self.setText(text)
        self.setIconSize(QSize(22, 22))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_icon(icon_path)

        default, hover, pressed = _button_colors(color)

        self.setStyleSheet(
            f"""
            QToolButton {{
                border: 1px solid #55555530;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: {default}18;
                color: palette(text);
            }}
            QToolButton:hover {{
                background-color: {hover}30;
            }}
            QToolButton:pressed {{
                background-color: {pressed}40;
            }}
            """
        )

    def set_icon(self, icon_path) -> None:
        self.setIcon(QIcon(str(icon_path)))


class AppButtonCheck(_AppIconButton):
    """Boton toggle activar/desactivar: check verde cuando esta activo
    (pulsar desactiva), cross rojo cuando esta inactivo (pulsar activa)."""

    _COLOR_ACTIVE = "#3fa34d"
    _COLOR_INACTIVE = "#e20c0c"

    def __init__(self, active: bool, text_active="Desactivar", text_inactive="Activar"):
        self._text_active = text_active
        self._text_inactive = text_inactive
        self._active = active
        super().__init__(self._label_for(active), self._color_for(active))
        self._icon_path = self._icon_for(active)
        self.setIcon(QIcon(str(self._icon_path)))

    def _label_for(self, active: bool) -> str:
        return self._text_active if active else self._text_inactive

    def _color_for(self, active: bool) -> str:
        return self._COLOR_ACTIVE if active else self._COLOR_INACTIVE

    def _icon_for(self, active: bool):
        return ACTION_CHECK if active else ACTION_CROSS

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setText(self._label_for(active))
        self.setIcon(QIcon(str(self._icon_for(active))))

        default, hover, pressed = _button_colors(self._color_for(active))
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

    def is_active(self) -> bool:
        return self._active
