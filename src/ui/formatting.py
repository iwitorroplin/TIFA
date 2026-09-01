from __future__ import annotations

from datetime import datetime

_MOMENT_FORMAT = "%d/%m/%Y %H:%M"


def format_moment(moment: datetime | None, now: datetime | None = None) -> str:
    """Fecha y hora con el "hace cuánto" / "en cuánto" al lado, que es lo que uno
    mira de un vistazo para saber si el backup está al día."""
    if moment is None:
        return "—"

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
