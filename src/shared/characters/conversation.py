"""
Conversaciones entre personajes:

Doble clic en un retrato de `MessageBar`
ese personaje arranca una charla;
cada OK pasa el turno al siguiente. 


Para añadir o cambiar una conversación solo hay que tocar `CONVERSATIONS`, aquí
abajo. Nada más de la aplicación depende de este fichero: se engancha en
`window_app.py` con una línea (`conversation.attach(...)`) y se quita igual.
"""

from __future__ import annotations

import random
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

# Para volver del prefijo de una clave de `CONVERSATIONS` (p.ej. "TIFA") al
# personaje que le corresponde.
_CHARACTERS_BY_NAME: dict[str, MessageType] = {
    "YUFI": YUFI,
    "TIFA": TIFA,
    "CLOUD": CLOUD,
    "SEPHIROTH": SEPHIROTH,
}


@dataclass(frozen=True)
class Line:
    """Una intervención: quién habla y qué dice."""

    speaker: MessageType
    text: str


def script(*lines: tuple[MessageType, str]) -> tuple[Line, ...]:
    """Escribe un guion como pares (personaje, frase), en orden."""
    return tuple(Line(speaker, text) for speaker, text in lines)


# Qué conversaciones puede arrancar cada retrato. Cada guion se nombra
# "PERSONAJE_NN" (NN entre "00" y "99"): el prefijo dice de quién es y el
# número solo distingue variantes entre sí, sin que importe el orden. Un
# personaje puede tener varias -o ninguna, y entonces el doble clic no hace
# nada-; si tiene más de una, cuál se cuenta es un sorteo en cada doble clic,
# porque la charla es anecdótica y no una secuencia que haya que agotar.




CONVERSATIONS: dict[str, tuple[Line, ...]] = {
    "TIFA_00": script(
        (TIFA, "Cloud, ¿has visto mis guantes?"),
        (CLOUD, "No."),
        (TIFA, "Están encima de tu espada."),
        (CLOUD, "...Ah."),
    ),

    "TIFA_01": script(
        (TIFA, "¿Has terminado el informe?"),
        (CLOUD, "Sí."),
        (TIFA, "¿Y lo has revisado?"),
        (CLOUD, "...No."),
        (CLOUD, "Lo revisaré."),
    ),

    "TIFA_02": script(
        (TIFA, "¿Sabes qué necesita esta aplicación?"),
        (CLOUD, "¿Qué?"),
        (TIFA, "Una barra para medir cuánto café queda en la máquina."),
        (CLOUD, "Eso no es una métrica."),
        (TIFA, "Lo será."),
    ),

    "YUFI_00": script(
        (YUFI, "¡He encontrado algo increíble!"),
        (CLOUD, "¿Qué has encontrado?"),
        (YUFI, "Una cosa que no estaba buscando."),
        (CLOUD, "Eso no responde a mi pregunta."),
        (YUFI, "¡Pero ahora es mía!"),
    ),

    "YUFI_01": script(
        (YUFI, "¿Quién ha dejado esto aquí?"),
        (TIFA, "Probablemente tú."),
        (YUFI, "Imposible."),
        (TIFA, "Tiene tu nombre."),
        (YUFI, "...Eso tampoco demuestra nada."),
    ),

    "YUFI_02": script(
        (YUFI, "Cloud, préstame tu espada."),
        (CLOUD, "No."),
        (YUFI, "Solo un momento."),
        (CLOUD, "No."),
        (YUFI, "Qué poco colaborador."),
    ),

    "CLOUD_00": script(
        (CLOUD, "Se terminado el ciclo de esterilización."),
        (TIFA, "¿Todo correcto?"),
        (CLOUD, ".... Sí."),
        (TIFA, "¿Seguro?"),
        (CLOUD, "...Casi."),
        (TIFA, "Eso no inspira mucha confianza."),
    ),

    "CLOUD_01": script(
        (CLOUD, "¿Has visto a Yufi?"),
        (TIFA, "Hace cinco minutos."),
        (CLOUD, "¿Y ahora?"),
        (TIFA, "Probablemente buscando algo que llevarse."),
        (CLOUD, "Entonces sabemos dónde está."),
    ),

    "CLOUD_02": script(
        (CLOUD, "Todo está en orden."),
        (SEPHIROTH, "No."),
        (CLOUD, "¿Qué no está en orden?"),
        (SEPHIROTH, "La interfaz."),
        (CLOUD, "..."),
        (SEPHIROTH, "Demasiado azul."),
    ),

    "SEPHIROTH_00": script(
        (SEPHIROTH, "¿Sabes qué es inevitable?"),
        (YUFI, "¿El tiempo?"),
        (SEPHIROTH, "Los errores sin leer."),
        (YUFI, "...Eso es bastante menos dramático."),
    ),

    "SEPHIROTH_01": script(
        (SEPHIROTH, "He observado el sistema."),
        (CLOUD, "¿Y?"),
        (SEPHIROTH, "Funciona."),
        (CLOUD, "¿Eso es todo?"),
        (SEPHIROTH, "Me decepciona admitirlo."),
    ),

    "SEPHIROTH_02": script(
        (SEPHIROTH, "Cloud."),
        (CLOUD, "¿Qué?"),
        (SEPHIROTH, "Tu informe tiene una errata."),
        (CLOUD, "¿Dónde?"),
        (SEPHIROTH, "Página tres."),
        (CLOUD, "..."),
        (SEPHIROTH, "Ahora sí tienes un enemigo."),
    ),

    "TIFA_03": script(
        (TIFA, "¿Crees que necesitamos otro botón?"),
        (CLOUD, "No."),
        (TIFA, "¿Y otro menú?"),
        (CLOUD, "No."),
        (TIFA, "¿Otra ventana?"),
        (CLOUD, "..."),
        (TIFA, "Vale, vale."),
    ),

    "YUFI_03": script(
        (YUFI, "¡He conseguido una cosa!"),
        (TIFA, "¿Dónde la has encontrado?"),
        (YUFI, "Eso es confidencial."),
        (TIFA, "¿La has robado?"),
        (YUFI, "Prefiero decir: Adquisición temporal de forma indefinida."),
    ),

    "YUFI_04": script(
        (YUFI, "¿Qué hace este botón?"),
        (TIFA, "No lo pulses."),
        (YUFI, "¿Por qué?"),
        (TIFA, "Porque no sabemos qué hace."),
        (YUFI, "Entonces hay que pulsarlo."),
        (CLOUD, "No."),
    ),

    "CLOUD_03": script(
        (CLOUD, "¿Por qué todos me llaman para solucionar cosas?"),
        (TIFA, "Porque normalmente las solucionas."),
        (CLOUD, "Ese es el problema."),
        (TIFA, "¿Que las solucionas?"),
        (CLOUD, "Que ahora esperan que lo haga siempre."),
    ),

    "SEPHIROTH_03": script(
        (SEPHIROTH, "Este sistema tiene una debilidad."),
        (TIFA, "¿Cuál?"),
        (SEPHIROTH, "El usuario."),
        (TIFA, "Eso no es una debilidad del sistema."),
        (SEPHIROTH, "Depende del usuario."),
    ),
    "SEPHIROTH_04": script(
        (SEPHIROTH, "Cloud."),
        (CLOUD, "Sephiroth."),
        (SEPHIROTH, "Nada."),
        (CLOUD, "..."),
    ),
}


def _character_of(key: str) -> MessageType:
    name = key.rsplit("_", 1)[0]
    character = _CHARACTERS_BY_NAME.get(name)
    if character is None:
        raise ValueError(f"Clave de conversación mal formada: {key!r} (se espera 'PERSONAJE_NN')")
    return character


# Índice real que usa el player: por personaje, la lista de guiones posibles.
# Se calcula una vez a partir de `CONVERSATIONS`, así que añadir un guion
# nuevo (o una variante más de uno que ya existe) sigue siendo tocar solo el
# dict de ahí arriba.
_CONVERSATIONS_BY_CHARACTER: dict[MessageType, list[tuple[Line, ...]]] = {}
for _key, _lines in CONVERSATIONS.items():
    _CONVERSATIONS_BY_CHARACTER.setdefault(_character_of(_key), []).append(_lines)
del _key, _lines


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
        candidates = _CONVERSATIONS_BY_CHARACTER.get(portrait)
        if candidates:
            self.play(random.choice(candidates))

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
