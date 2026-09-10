"""Visor de log tipo terminal que colorea cada línea según su nivel.

Toda línea de log tiene la forma `[fecha] [NIVEL] [ÁMBITO] texto` (ver
`src/shared/logs/logger.py`). Aquí se usa ese nivel para lo único que no puede
hacer el fichero: que un ERROR entre cientos de INFO se vea sin leerlos todos.

El nivel se lee del texto y no de un objeto: lo que se muestra es un fichero
que puede haber escrito otra ejecución -o la de ayer-, no un mensaje que
acabe de pasar por el `MessageManager`. Una línea sin nivel reconocible (un
log antiguo, o el volcado de otra herramienta) se pinta con el color normal en
vez de perderse.
"""

from __future__ import annotations

import re
from html import escape

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit

from src.shared.messages.types import MessageType

_BACKGROUND = "#1e1e1e"
_FOREGROUND = "#d4d4d4"

# Colores sobre fondo oscuro, no los de los personajes (`senders.py`): allí se
# eligieron para leerse sobre la barra de mensajes, que es clara.
_LEVEL_COLORS = {
    MessageType.ERROR.name: "#ff6b6b",
    MessageType.WARNING.name: "#e0a800",
    MessageType.SUCCESS.name: "#6fcf7f",
    MessageType.INFO.name: _FOREGROUND,
}

_RE_LEVEL = re.compile(r"^\[[^\]]+\]\s*\[([A-Z]+)\]")


class LogTextView(QPlainTextEdit):
    """Solo lectura, monoespaciado y sin ajuste de línea, como una consola."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {_BACKGROUND}; color: {_FOREGROUND}; }}"
        )

    def set_log_text(self, text: str) -> None:
        """Reemplaza todo el contenido (al abrir otra ejecución de log)."""
        self.clear()
        self.append_log_text(text)

    def append_log_text(self, text: str) -> None:
        """Añade lo que ha crecido el fichero desde la última lectura."""
        for linea in text.rstrip("\n").splitlines():
            self.appendHtml(_como_html(linea))

    def scroll_to_bottom(self) -> None:
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def _como_html(linea: str) -> str:
    # `appendHtml` interpreta el texto como HTML, así que hay que escapar la
    # línea entera: las rutas y los mensajes de error traen '<', '>' y '&' que
    # si no desaparecerían de la pantalla como si fueran etiquetas.
    contenido = escape(linea)
    match = _RE_LEVEL.match(linea)
    color = _LEVEL_COLORS.get(match.group(1)) if match else None
    if color is None or color == _FOREGROUND:
        return f"<span style='white-space: pre'>{contenido}</span>"
    return f"<span style='white-space: pre; color: {color}'>{contenido}</span>"
