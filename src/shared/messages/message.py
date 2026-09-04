from dataclasses import dataclass, field
from datetime import datetime

from src.shared.messages.types import Delivery, MessageType, Module


@dataclass(frozen=True)
class Message:
    """Mensaje real emitido por un módulo, con quién lo originó y cuándo.

    El remitente (personaje) y el color se resuelven aparte a partir de
    `type`, vía `SENDERS`/`ACCENT_COLORS` en `src.shared.characters.senders`:
    son fijos por severidad, no por módulo. `delivery` decide si además se
    anuncia con un personaje o si se queda solo en el historial.
    """

    module: Module
    type: MessageType
    text: str
    delivery: Delivery = Delivery.CHARACTER
    timestamp: datetime = field(default_factory=datetime.now)
