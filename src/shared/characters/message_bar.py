from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.shared.characters.message_box import MessageBox
from src.shared.characters.portrait import tinted_portrait
from src.shared.characters.senders import ACCENT_COLORS, SENDERS
from src.shared.messages.manager import manager
from src.shared.messages.message import Message
from src.shared.messages.types import MessageType

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
    los módulos disparan con `Logger.log(..., talk=...)` (o `manager.push(...)`
    para un aviso que no va al log), no llamando a este widget directamente.

    Lo único que expone hacia fuera es `portraitDoubleClicked`: la barra sabe
    qué retrato se ha pulsado, pero no qué hacer con eso -de las conversaciones
    se encarga `conversation.py`, que es un añadido y no parte del sistema de
    avisos-.
    """

    portraitDoubleClicked = Signal(MessageType)

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
            # QLabel no tiene señal de doble clic: se filtra el evento y se
            # reemite ya diciendo de qué retrato viene.
            label.installEventFilter(self)
            self._portrait_labels[message_type] = label
            layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._refresh_portraits()
        manager.messagePushed.connect(self._on_message_pushed)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            for message_type, label in self._portrait_labels.items():
                if watched is label:
                    self.portraitDoubleClicked.emit(message_type)
                    return True
        return super().eventFilter(watched, event)

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
        # Un mensaje nuevo sustituye al anterior en vez de apilarse: aquí solo
        # se ve lo inmediato -lo acumulado se consulta en la pestaña Logs-.
        if self._message_box is not None:
            self._message_box.close()

        self._talking_type = message.type
        self._refresh_portraits()

        window = self.window()
        box = MessageBox(message.type, message.text, parent=window)
        box.closed.connect(lambda: self._on_message_closed(box))

        # El cuadro es una ventana propia (ver MessageBox), así que move() va
        # en coordenadas de pantalla: se centra sobre la ventana principal, no
        # sobre este widget.
        center = window.frameGeometry().center()
        box.move(center.x() - box.width() // 2, center.y() - box.height() // 2)

        box.show()
        box.raise_()
        # Foco de teclado, para que el OK responda a Intro y Esc cierre.
        box.activateWindow()
        self._message_box = box

    def _on_message_closed(self, box: MessageBox) -> None:
        if box is not self._message_box:
            return
        self._message_box = None
        self._talking_type = None
        self._refresh_portraits()
