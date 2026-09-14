"""Texto listo para mostrar a partir de fechas, números y duraciones.

Sin Qt y fuera de `ui/` a propósito: `logic/` también lo usa (las celdas de
`steriflow/logic/sterilization/columns.py`), y así la tabla en pantalla, la
impresión y cualquier otro módulo formatean igual sin repetir cada uno sus
propios formateadores.
"""

from __future__ import annotations

from datetime import datetime

# Lo que se pinta cuando no hay valor: una celda vacía se confunde con "no
# cargó", un guion largo dice "no aplica".
MISSING = "—"

_MOMENT_FORMAT = "%d/%m/%Y %H:%M"
_DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"


def format_decimal(value: float | None, digits: int) -> str:
    return MISSING if value is None else f"{value:.{digits}f}"


def format_datetime(value: datetime | None) -> str:
    return MISSING if value is None else value.strftime(_DATETIME_FORMAT)


def format_duration_hms(seconds: float | None) -> str:
    if seconds is None:
        return MISSING
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_moment(moment: datetime | None, now: datetime | None = None) -> str:
    """Fecha y hora con el "hace cuánto" / "en cuánto" al lado, que es lo que uno
    mira de un vistazo para saber si el backup está al día."""
    if moment is None:
        return MISSING

    reference = now if now is not None else datetime.now()
    return f"{moment:{_MOMENT_FORMAT}} ({_relative(moment, reference)})"


def _relative(moment: datetime, now: datetime) -> str:
    total_minutes = round((moment - now).total_seconds() / 60)
    upcoming = total_minutes > 0
    minutes = abs(total_minutes)

    if minutes < 1:
        return "ahora"
    if minutes < 60:
        amount = f"{minutes} min"
    elif minutes < 60 * 24:
        hours = minutes // 60
        amount = "1 hora" if hours == 1 else f"{hours} horas"
    else:
        days = minutes // (60 * 24)
        amount = "1 día" if days == 1 else f"{days} días"

    return f"en {amount}" if upcoming else f"hace {amount}"
