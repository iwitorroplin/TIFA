from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.ui.components.message_box import MessageBox
from src.ui.messages.manager import manager
from src.ui.messages.messages import ACCENT_COLORS, Message, SENDERS, tinted_portrait
from src.ui.messages.types import MessageType

_PORTRAIT_SIZE = 96

# Retrato sin teñir: el personaje que no está hablando queda "en silencio".
_SILENT_COLOR = QColor("#ffffff")

_PORTRAIT_ORDER = (
    MessageType.SUCCESS,
    MessageType.INFO,
    MessageType.WARNING,
    MessageType.ERROR,
)


class MessageBar(QWidget):
    """Columna vertical a la derecha de la ventana, simétrica a Navbar a la
    izquierda (ver window_app.py): quién está hablando y el MessageBox del
    último mensaje, sin importar la página activa. Solo escucha `manager`:
    los módulos disparan con `manager.push(...)`, no llamando a este widget
    directamente.
    """

    def __init__(self):
        super().__init__()
        self.setFixedWidth(160)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._message_box = None
        self._talking_type = None
        self._portrait_labels: dict[MessageType, QLabel] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.addStretch()
        for message_type in _PORTRAIT_ORDER:
            label = QLabel()
            label.setFixedSize(_PORTRAIT_SIZE, _PORTRAIT_SIZE)
            self._portrait_labels[message_type] = label
            layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._refresh_portraits()
        manager.messagePushed.connect(self._on_message_pushed)

    def _refresh_portraits(self) -> None:
        for message_type, label in self._portrait_labels.items():
            sender = SENDERS[message_type]
            color = (
                ACCENT_COLORS[message_type]
                if self._talking_type == message_type
                else _SILENT_COLOR
            )
            label.setPixmap(tinted_portrait(sender, color, _PORTRAIT_SIZE))

    def _on_message_pushed(self, message: Message) -> None:
        if self._message_box is not None:
            self._message_box.close()

        self._talking_type = message.type
        self._refresh_portraits()

        box = MessageBox(message.type, message.text, parent=self.window())
        box.closed.connect(lambda: self._on_message_closed(box))
        box.move(
            (self.window().width() - box.width()) // 2,
            (self.window().height() - box.height()) // 2,
        )
        box.show()
        box.raise_()
        self._message_box = box

    def _on_message_closed(self, box: MessageBox) -> None:
        if box is not self._message_box:
            return
        self._message_box = None
        self._talking_type = None
        self._refresh_portraits()
