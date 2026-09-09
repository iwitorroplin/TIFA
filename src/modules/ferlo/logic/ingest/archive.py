"""D1: dos carpetas, ninguna tabla.

`entrada/<machine>/` es un buzón transitorio -el operario deja aquí lo que
haya exportado y, tras importar, queda vacío-. `archivo/<machine>/` es la
capa cruda de verdad: un CSV por máquina y mes, que TIFA nombra y mantiene.
Al mensual **solo se le añade** -nunca se reescribe ni se reordena-: en
cuanto TIFA empieza a escribir la capa cruda, escribir de más es la única
operación que no puede perder lo que ya había.

Las dos cabeceras se reescriben tal cual las trae el origen (ver
`logic/ingest/reader.py`): así el mensual sigue siendo un CSV Ferlo normal,
legible por el mismo lector, si alguna vez hay que revisarlo a mano.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .reader import ENCODING, RawRow

_HEADER_1 = ["Hora", "Hora", "TEMP", "PRES"]
_HEADER_2 = ["Fecha dd/MM/yyyy", "Hora H:mm:ss", "Valor °C", "Valor bar"]


def monthly_archive_path(archivo_root: Path, machine: str, year: int, month: int) -> Path:
    return archivo_root / machine / f"{machine}_M{year:04d}{month:02d}.csv"


def _year_month(date_raw: str) -> tuple[int, int]:
    dia, mes, anio = date_raw.split("/")
    return int(anio), int(mes)


def group_by_month(rows: list[RawRow]) -> dict[tuple[int, int], list[RawRow]]:
    """Agrupa por el mes que dice `date_raw` -no por el mes en que se
    importa-: una entrada puede traer el cierre de un mes y el arranque del
    siguiente en el mismo fichero."""
    grupos: dict[tuple[int, int], list[RawRow]] = {}
    for row in rows:
        grupos.setdefault(_year_month(row.date_raw), []).append(row)
    return grupos


def append_rows(
    archivo_root: Path, machine: str, year: int, month: int, rows: list[RawRow]
) -> Path:
    """Añade `rows` al mensual de `machine`/`year`-`month`; lo crea con sus
    dos cabeceras si todavía no existe. `rows` ya viene filtrado a lo nuevo
    -ver `logic/ingest/service.py`-: aquí no se decide qué es nuevo."""
    path = monthly_archive_path(archivo_root, machine, year, month)
    es_nuevo = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding=ENCODING) as f:
        writer = csv.writer(f, delimiter="\t")
        if es_nuevo:
            writer.writerow(_HEADER_1)
            writer.writerow(_HEADER_2)
        for row in rows:
            writer.writerow([row.date_raw, row.time_raw, row.temperature_raw, row.pressure_raw])
    return path
