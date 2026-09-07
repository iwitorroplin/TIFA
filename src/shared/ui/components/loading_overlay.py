from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from src.shared.ui.components.app_button import AppStopButton

# Aunque la acción termine al instante, se queda visible este mínimo: sin
# esto, una acción rápida parpadea en vez de dar la sensación de que ha
# pasado algo.
_MIN_VISIBLE_MS = 1000


class LoadingOverlay(QWidget):
    """Cubre `parent` mientras dura un proceso largo.

    Al ser un widget hijo que se pone encima y a pantalla completa, los clics
    quedan bloqueados para todo lo que hay debajo sin tener que deshabilitar
    cada botón a mano en cada acción.

    No cancela nada por sí solo: `cancelled` solo avisa de que el usuario ha
    pedido cancelar, y quien llame a `start(cancellable=True)` es quien debe
    saber parar la acción en curso.
    """

    cancelled = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")

        # Guardado aparte y no vía self.parentWidget(): ese getter devuelve
        # QWidget | None (podría reparentarse a nadie), y aquí sabemos que
        # siempre hay un contenedor fijo -el mismo que se nos pasó-.
        self._container = parent
        parent.installEventFilter(self)

        self._label = QLabel()
        self._label.setStyleSheet("color: white; font-size: 14px;")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(240)
        self._progress.setTextVisible(False)

        self._cancel_button = AppStopButton("Cancelar")
        self._cancel_button.clicked.connect(self.cancelled.emit)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self._min_visible_timer = QTimer(self)
        self._min_visible_timer.setSingleShot(True)
        self._min_visible_timer.timeout.connect(self._hide_if_finish_pending)
        self._finish_pending = False

        self.hide()

    def start(self, text: str = "", *, cancellable: bool = False, indeterminate: bool = True) -> None:
        self._label.setText(text)
        self._label.setVisible(bool(text))
        self._progress.setRange(0, 0 if indeterminate else 100)
        self._progress.setValue(0)
        self._cancel_button.setVisible(cancellable)
        self._finish_pending = False

        self.setGeometry(self._container.rect())
        self.raise_()
        self.show()
        self._min_visible_timer.start(_MIN_VISIBLE_MS)

    def set_progress(self, value: int) -> None:
        """Solo tiene efecto tras `start(indeterminate=False)`."""
        self._progress.setValue(value)

    def finish(self) -> None:
        if self._min_visible_timer.isActive():
            self._finish_pending = True
        else:
            self.hide()

    def eventFilter(self, watched, event):
        if watched is self._container and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._container.rect())
        return super().eventFilter(watched, event)

    def _hide_if_finish_pending(self) -> None:
        if self._finish_pending:
            self.hide()
