"""Conversaciones entre personajes: el guiño, no el sistema de avisos.

Doble clic en un retrato de `MessageBar` y ese personaje arranca una charla;
cada OK pasa el turno al siguiente. No es un `Message` ni pasa por `manager`:
no es información que le haga falta a nadie, no deja rastro en el log y no
tiene severidad -Tifa aquí no anuncia un éxito, solo habla-.

Lo que sí reusa es toda la estructura de `shared/characters`: el mismo
`MessageBox`, los mismos retratos y colores de `senders.py`, y el mismo índice
por `MessageType`. Por eso el guion se escribe con los nombres de los
personajes (`TIFA`, `CLOUD`...), que son alias de esa misma clave: dentro es el
sistema de siempre, fuera se lee como un diálogo.

Para añadir o cambiar una conversación solo hay que tocar `CONVERSATIONS`, aquí
abajo. Nada más de la aplicación depende de este fichero: se engancha en
`window_app.py` con una línea (`conversation.attach(...)`) y se quita igual.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, Qt

from src.shared.characters.message_box import MessageBox
from src.shared.messages.manager import manager
from src.shared.messages.types import MessageType

# Los personajes están indexados por severidad (ver `senders.py`): estos alias
# son esa misma clave con el nombre por el que se les conoce, para que un guion
# no se lea como "SUCCESS dice...".
YUFI = MessageType.INFO
TIFA = MessageType.SUCCESS
CLOUD = MessageType.WARNING
SEPHIROTH = MessageType.ERROR


@dataclass(frozen=True)
class Line:
    """Una intervención: quién habla y qué dice."""

    speaker: MessageType
    text: str


def script(*lines: tuple[MessageType, str]) -> tuple[Line, ...]:
    """Escribe un guion como pares (personaje, frase), en orden."""
    return tuple(Line(speaker, text) for speaker, text in lines)


# Qué conversación arranca cada retrato. Un retrato sin entrada aquí
# simplemente no hace nada al doble clic.
CONVERSATIONS: dict[MessageType, tuple[Line, ...]] = {
    TIFA: script(
        (TIFA, "Ya está todo copiado. ¿Ves? No era tan difícil."),
        (CLOUD, "Lo difícil no es copiar. Es acordarse de mirar si salió bien."),
        (TIFA, "Para eso está la pestaña de Logs. Ahí queda todo, aunque nadie mire."),
    ),
    YUFI: script(
        (YUFI, "¡Eh, eh! ¿Has visto cuántos informes he traído hoy de las autoclaves?"),
        (SEPHIROTH, "Ninguno. Estaban apagadas."),
        (YUFI, "...Vale. Pero los habría traído."),
    ),
    CLOUD: script(
        (CLOUD, "Una de las autoclaves no respondía esta mañana."),
        (TIFA, "¿Y el backup?"),
        (CLOUD, "Siguió con las demás. Una máquina apagada no puede parar a las otras."),
        (TIFA, "Por eso el aviso salió amarillo y no rojo."),
    ),
    SEPHIROTH: script(
        (SEPHIROTH, "¿Sabes qué le pasa a un error que nadie lee?"),
        (YUFI, "¿...Que se queda en el log?"),
        (SEPHIROTH, "Que vuelve."),
    ),
}


class ConversationPlayer(QObject):
    """Va sacando las líneas de un guion, una por cuadro.

    Los cuadros se crean con `auto_close=False`, así que esperan al usuario en
    vez de irse solos: una conversación se lee al ritmo de quien la lee. OK
    pasa a la siguiente línea; Esc abandona la conversación entera.
    """

    def __init__(self, message_bar):
        super().__init__(message_bar)

        self._message_bar = message_bar
        self._pending: list[Line] = []
        self._box: MessageBox | None = None

        message_bar.portraitDoubleClicked.connect(self.play_for)
        # Un aviso de verdad siempre gana: si el backup termina (o falla) a
        # mitad de la charla, la charla se corta y no se queda un cuadro de
        # adorno tapando lo que importa.
        manager.messagePushed.connect(self._on_real_message)

    def play_for(self, portrait: MessageType) -> None:
        lines = CONVERSATIONS.get(portrait)
        if lines:
            self.play(lines)

    def play(self, lines) -> None:
        self.stop()
        self._pending = list(lines)
        self._show_next()

    def stop(self) -> None:
        self._pending.clear()
        box, self._box = self._box, None
        if box is not None:
            box.close()

    def _show_next(self) -> None:
        if not self._pending:
            self._box = None
            return

        line = self._pending.pop(0)
        window = self._message_bar.window()

        box = MessageBox(line.speaker, line.text, parent=window, auto_close=False)
        box.closed.connect(self._on_box_closed)
        box.installEventFilter(self)

        # Igual que en MessageBar: el cuadro es una ventana propia, así que se
        # centra en coordenadas de pantalla.
        center = window.frameGeometry().center()
        box.move(center.x() - box.width() // 2, center.y() - box.height() // 2)

        box.show()
        box.raise_()
        box.activateWindow()
        self._box = box

    def _on_box_closed(self) -> None:
        # Con `_box` ya a None la conversación estaba cancelada (por Esc o por
        # un aviso real) y este cierre es consecuencia, no un avance.
        if self._box is None:
            return
        self._box = None
        self._show_next()

    def _on_real_message(self, _message) -> None:
        self.stop()

    def eventFilter(self, watched, event):
        # Antes de que el cuadro procese su propio Esc: ahí Esc solo cierra
        # ese cuadro, y cerrarlo pasaría a la línea siguiente. Aquí significa
        # "déjalo ya", que es lo que espera quien lo pulsa.
        if (
            watched is self._box
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Escape
        ):
            self.stop()
            return True
        return super().eventFilter(watched, event)


def attach(message_bar) -> ConversationPlayer:
    """Engancha las conversaciones a la columna de personajes. El player queda
    como hijo de `message_bar`, así que vive y muere con ella."""
    return ConversationPlayer(message_bar)
