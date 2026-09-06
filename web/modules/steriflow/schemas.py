"""Esquemas Pydantic de la API de Steriflow: entrada y salida.

Sustituyen la validación manual que antes vivía en el handler HTTP a mano
sobre `http.server` -FastAPI la aplica sola contra `SteriflowReadingIn` y
devuelve un error si no cumple, así que `routes.py` ya no comprueba tipos ni
rangos por su cuenta.
"""

from __future__ import annotations

import datetime as dt
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# No es paranoia de seguridad: un dedo torpe en el móvil mete 356 en vez de
# 35.6, y ese dato acaba metido en la media de alguien.
_TEMP_MIN_C = -50.0
_TEMP_MAX_C = 200.0


class SteriflowReadingIn(BaseModel):
    temp_c: float = Field(ge=_TEMP_MIN_C, le=_TEMP_MAX_C, allow_inf_nan=False)
    created_by: str = ""
    note: str = ""

    _LIMITS: ClassVar[dict[str, int]] = {"created_by": 120, "note": 500}

    @field_validator("created_by", "note")
    @classmethod
    def _limpiar(cls, value: str, info: ValidationInfo) -> str:
        # Truncado, no rechazado: el campo obligatorio es la temperatura, no
        # hundir un envío bueno por una nota demasiado larga.
        return value.strip()[: cls._LIMITS[info.field_name]]


class SteriflowReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    temp_c: float
    created_by: str
    note: str
    created_at: dt.datetime
