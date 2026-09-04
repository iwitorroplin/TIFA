from enum import Enum


class MessageType(Enum):
    """Severidad de un mensaje. Determina qué personaje lo dice y de qué
    color se tiñe (ver src/shared/characters/senders.py):
    info -> Yufi, success -> Tifa, warning -> Cloud, error -> Sephiroth.

    DEBUG es la excepción: no lo dice ningún personaje. `MessageManager.push`
    fuerza `Delivery.SILENT` siempre que el tipo sea DEBUG, así que no hace
    falta (ni tiene sentido) darle entrada en SENDERS/ACCENT_COLORS.
    """

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


class Module(Enum):
    """Módulo que origina un mensaje. Los mismos nombres que usan Navbar y
    LogsView para sus pestañas."""

    HOME = "home"
    FERLO = "ferlo"
    STERIFLOW = "steriflow"
    MACONA = "macona"
    PASTEURIZATION = "pasteurization"
    CONFIG = "config"
    LOGS = "logs"
    PRUEBA_UI = "prueba_ui"


class Delivery(Enum):
    """Cómo se presenta un mensaje al usuario, además de quedar siempre en
    `MessageManager.history`."""

    # Lo anuncia un personaje: retrato + MessageBox emergente.
    CHARACTER = "character"
    # Solo historial (y logs): no interrumpe con un popup.
    SILENT = "silent"
