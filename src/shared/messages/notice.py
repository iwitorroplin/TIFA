from __future__ import annotations

from dataclasses import dataclass

from src.shared.logs.logger import Logger
from src.shared.messages.manager import manager
from src.shared.messages.types import MessageType, Module


@dataclass(frozen=True)
class Notice:
    """Un aviso ya redactado -qué se dice y con qué severidad- sin decidir
    todavía por qué canal sale. `Message` (message.py) es lo que ya viaja por
    el bus, con módulo puesto; un Notice aún no está atado a ninguno.

    La severidad va aquí dentro y no en el sitio de la llamada porque suele
    ser dato, no decoración: quien redacta el texto es quien sabe, por
    ejemplo, si una operación terminó con incidencias o no.
    """

    type: MessageType
    text: str


def announce(logger: Logger, notice: Notice) -> None:
    """Deja constancia en el log del módulo y además lo dice el personaje de
    esa severidad -equivale a `logger.log(notice.text, talk=notice.type)`.

    Úsalo cuando el aviso forma parte de un proceso con historial: así sale
    igual venga de un botón o de un scheduler en segundo plano, sin que la
    interfaz tenga que repetir el texto."""
    logger.log(notice.text, talk=notice.type)


def push(module: Module, notice: Notice) -> None:
    """Solo el bus, sin dejar rastro en ningún log. Úsalo para lo que es
    respuesta directa a un clic y no un paso de un proceso -no queda nada que
    consultar después, se dice y ya está."""
    manager.push(module, notice.type, notice.text)
