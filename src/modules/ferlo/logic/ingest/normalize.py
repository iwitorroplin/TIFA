"""Etapa 2 - de `RawRow` a muestra normalizada.

Portado de `legacy/sterilization_data_ferlo/src/formatter.py` (que lo hacía
en SQL, con `substr`/`GLOB`; aquí en Python, para poder probarlo sin abrir
una base -ver invariantes de la Fase 0-). Dos reglas, y ninguna fila se tira:

  instante = dd/MM/yyyy + H:mm:ss -> datetime
             (la hora se rellena a 8 caracteres antes de unir: '7:11:57' no
             es '07:11:57' en orden alfabetico, y el ciclo que las cruza
             quedaría partido)
  valor    = coma decimal a punto, solo si son dígitos/coma/punto/guion y hay
             al menos un dígito; cualquier otra cosa (vacío, '<<<<<<<<') ->
             None, sin descartar la fila -la temperatura puede seguir siendo
             buena aunque la presión no lea-.
"""

from __future__ import annotations

import datetime as dt

from src.modules.ferlo.logic.analysis.models import Series

from .reader import RawRow

_NUMERIC_CHARS = set("0123456789,.-")


def parse_timestamp(date_raw: str, time_raw: str) -> dt.datetime:
    dia, mes, anio = date_raw.split("/")
    hora = time_raw if len(time_raw) >= 8 else "0" + time_raw
    return dt.datetime.strptime(f"{anio}-{mes}-{dia} {hora}", "%Y-%m-%d %H:%M:%S")


def parse_numeric(raw: str | None) -> float | None:
    if not raw:
        return None
    if not (set(raw) <= _NUMERIC_CHARS and any(c.isdigit() for c in raw)):
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def normalize_row(row: RawRow) -> tuple[dt.datetime, float | None, float | None]:
    return (
        parse_timestamp(row.date_raw, row.time_raw),
        parse_numeric(row.temperature_raw),
        parse_numeric(row.pressure_raw),
    )


def build_series(machine: str, source_filename: str, rows: list[RawRow]) -> Series:
    """Normaliza `rows` entero y lo deja listo para `logic/analysis/`.

    `autoclave_id` no significa nada para Ferlo -la identidad es `machine`,
    una cadena ("F2"), no un id numerico-; se deja a 0 porque nada en
    `logic/analysis/` lo lee (ver `CycleResult`/`repo.save_cycle`, que reciben
    `machine` aparte).
    """
    serie = Series(autoclave_id=0, autoclave_name=machine, source_filename=source_filename)
    for row in rows:
        ts, temp, pres = normalize_row(row)
        serie.ts.append(ts)
        serie.temperature_c.append(temp)
        serie.pressure_bar.append(pres)
    return serie
