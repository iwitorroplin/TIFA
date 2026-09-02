"""Conversión de fechas para columnas SQLite (que no tienen tipo TEXT nativo
de fecha): mismo formato ISO 8601 para que todos los módulos ordenen y
comparen fechas como texto sin ambigüedad.
"""

from __future__ import annotations

import datetime as dt


def to_iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def from_iso(value: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(value) if value is not None else None
