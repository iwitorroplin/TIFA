import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QFont, QTextOption
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QWidget,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
)

from src.shared.characters.portrait import tinted_portrait
from src.shared.characters.senders import ACCENT_COLORS, SENDERS
from src.shared.messages.types import MessageType

_PORTRAIT_SIZE = 96

# Ancho fijo; el alto se ajusta al contenido (ver __init__) entre estos dos
# límites -antes el cuadro era 560x210 fijo y un mensaje largo simplemente se
# cortaba sin aviso más allá de esos 210px-.
_WIDTH = 640
_MIN_HEIGHT = 210
_MAX_HEIGHT = 480

# El marco exterior del cuadro siempre es blanco; solo el nombre y el
# retrato se tiñen según el tipo de mensaje.
_BORDER_COLOR = QColor("#ffffff")


class MessageBox(QWidget):

    # Se emite al cerrarse, para que quien la muestre sepa que el
    # personaje ha dejado de hablar (ver HomeView._on_message_closed).
    closed = Signal()

    def __init__(
        self,
        message_type=MessageType.INFO,
        message="Operación completada correctamente.",
        parent=None,
    ):
        super().__init__(parent)

        self._accent_color = ACCENT_COLORS[message_type]
        sender = SENDERS[message_type]

        self.setFixedWidth(_WIDTH)

        # Retrato del personaje que envía el mensaje, con el fondo teñido
        # del color del tipo de mensaje.
        self.portrait = QLabel()
        self.portrait.setFixedSize(_PORTRAIT_SIZE, _PORTRAIT_SIZE)
        self.portrait.setPixmap(
            tinted_portrait(sender, self._accent_color, _PORTRAIT_SIZE)
        )

        # Nombre del personaje, coloreado según el tipo de mensaje
        self.name_label = QLabel(sender.name)
        self.name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        # Texto. QTextEdit y no QLabel: WrapAtWordBoundaryOrAnywhere rompe
        # una "palabra" sin espacios que sea más ancha que la caja -un QLabel
        # con word-wrap normal no la parte, se sale del ancho sin avisar-, y
        # de paso ya trae scroll propio para el caso de texto muy largo.
        self.message_label = QTextEdit()
        self.message_label.setPlainText(message)
        self.message_label.setReadOnly(True)
        self.message_label.setFrameShape(QFrame.Shape.NoFrame)
        self.message_label.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.message_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.message_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_label.setFont(QFont("Arial", 14))

        # Botón
        self.ok_button = QPushButton("OK")
        self.ok_button.setFixedSize(90, 32)
        self.ok_button.setFont(QFont("Arial", 11))
        self.ok_button.clicked.connect(self.close)

        # Columna de texto: nombre + mensaje
        self._text_layout = QVBoxLayout()
        self._text_layout.setSpacing(6)
        self._text_layout.addWidget(self.name_label)
        self._text_layout.addWidget(self.message_label)
        self._text_layout.addStretch()

        # Fila superior: retrato + columna de texto
        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)
        content_layout.addWidget(
            self.portrait, alignment=Qt.AlignmentFlag.AlignTop
        )
        content_layout.addLayout(self._text_layout)

        # Layout botón
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(10)

        layout.addLayout(content_layout)
        layout.addStretch()
        layout.addLayout(button_layout)

        # Estilos internos
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: {self._accent_color.name()};
                background: transparent;
            }}
        """)

        self.message_label.setStyleSheet("""
            QTextEdit {
                color: white;
                background: transparent;
                border: none;
            }
        """)

        self.ok_button.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(20, 35, 65, 180);
                border: 2px solid white;
                border-radius: 6px;
            }

            QPushButton:hover {
                background-color: rgba(60, 80, 120, 220);
            }

            QPushButton:pressed {
                background-color: rgba(100, 120, 160, 220);
            }
        """)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Alto dinámico: una primera pasada de layout con adjustSize() da la
        # geometría real (incluido el ancho de viewport de message_label ya
        # descontado su marco interno), así "overhead" -todo lo que NO es el
        # texto: márgenes, nombre, botón...- sale de restar en vez de
        # adivinar constantes de margen a mano.
        self.adjustSize()
        overhead = self.height() - self.message_label.height()

        document = self.message_label.document()
        document.setTextWidth(self.message_label.viewport().width())
        text_height = int(document.size().height()) + 4

        natural_height = overhead + text_height
        if natural_height > _MAX_HEIGHT:
            self.message_label.setFixedHeight(max(20, _MAX_HEIGHT - overhead))
            self.setFixedHeight(_MAX_HEIGHT)
        else:
            self.message_label.setFixedHeight(text_height)
            self.setFixedHeight(max(_MIN_HEIGHT, natural_height))

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # -------------------------------------------------
        # MARCO EXTERIOR (siempre blanco)
        # -------------------------------------------------

        outer_rect = self.rect().adjusted(2, 2, -2, -2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_BORDER_COLOR)

        painter.drawRoundedRect(
            outer_rect,
            14,
            14
        )

        # -------------------------------------------------
        # INTERIOR
        # -------------------------------------------------

        border_width = 5

        inner_rect = outer_rect.adjusted(
            border_width,
            border_width,
            -border_width,
            -border_width
        )

        # Degradado azul → negro
        gradient = QLinearGradient(
            0,
            inner_rect.top(),
            0,
            inner_rect.bottom()
        )

        gradient.setColorAt(0.0, QColor("#17366f"))
        gradient.setColorAt(0.45, QColor("#0b1d40"))
        gradient.setColorAt(1.0, QColor("#000000"))

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)

        painter.drawRoundedRect(
            inner_rect,
            9,
            9
        )

# ---------------------------------------------------------
# DEMO
# ---------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("MessageBox Preview")
    window.resize(800, 500)

    layout = QVBoxLayout(window)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    message_box = MessageBox(
        MessageType.SUCCESS,
        "Operación completada correctamente.",
    )

    layout.addWidget(message_box)

    window.show()

    sys.exit(app.exec())
