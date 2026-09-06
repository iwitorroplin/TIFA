from dataclasses import dataclass, field
from datetime import datetime

from src.shared.messages.types import MessageType, Module


@dataclass(frozen=True)
class Message:
    """Un aviso puntual para el usuario, en el momento en que ocurre.

    No es una entrada de historial: lo que hay que poder consultar después
    vive en el log del módulo (pestaña Logs del navbar). El remitente
    (personaje) y el color se resuelven aparte a partir de `type`, vía
    `SENDERS`/`ACCENT_COLORS` en `src.shared.characters.senders`: son fijos
    por severidad, no por módulo.
    """

    module: Module
    type: MessageType
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
