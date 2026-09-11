"""Etapa 1 - Lectura del CSV de Ferlo, tal cual.

Portado de `legacy/sterilization_data_ferlo/src/importer.py`. Cuatro columnas
por POSICION, no por nombre: la primera cabecera del CSV rotula la columna de
fecha como "Hora" -solo la segunda cabecera dice el formato real-, así que
fiarse del nombre de columna cruzaría fecha y hora en los 80 ficheros a la
vez (ver invariantes de la Fase 0). cp1252 y no UTF-8 porque la cabecera trae
"M-0C" -un "°C" mal codificado por el equipo-.

El delimitador y la codificación no son siempre los mismos: el mismo tipo de
CSV llega distinto según si se exportó directo del software de la máquina o
si pasó por un Excel intermedio (';', UTF-8 con BOM). `read_raw_rows` detecta
ambos con `shared/utils/csv_format.py` en vez de asumir un único formato fijo
-y avisa por log cuando detecta algo distinto del formato de máquina
original, para que quede constancia de qué exportación se está leyendo-.

La fecha, en cambio, solo se acepta en dd/MM/yyyy (el único formato que trae
el software de la máquina; opcionalmente con una hora pegada en la misma
celda, que Excel a veces concatena al reformatear la columna). Cualquier otra
forma -incluida una fecha con pinta de ISO, "2026-09-10 00:00:00"- NO se
interpreta como un formato alternativo válido: es la marca de que un Excel
intermedio autoformateó la celda y la dejó fija en un valor repetido durante
miles de filas mientras la hora seguía avanzando bien (visto en Ferlo1.csv).
Adivinar la fecha real a partir de la hora sería inventar un dato; se
prefiere descartar esas filas y decirlo claro en el log (etapa 1: "nada se ha
interpretado todavía", pero una fecha ilegible no es una fila, así que aquí sí
se filtra -ver invariante de "ninguna fila se tira" en `normalize.py`, que es
de la etapa 2 en adelante-.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.shared.utils.csv_format import detect_delimiter as _detect_delimiter
from src.shared.utils.csv_format import detect_encoding as _detect_encoding

ENCODING = "cp1252"
_DELIMITERS = ("\t", ";", ",", "|")

# dd/MM/yyyy (único formato de fecha que trae la máquina) opcionalmente
# seguido de una hora que el propio Excel a veces concatena en la misma
# celda ("10/09/2026 16:02:30"); esa hora se ignora aquí, la manda `time_raw`.
_FECHA_DMY_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+\d{1,2}:\d{2}(?:\:\d{2})?)?$")


@dataclass(slots=True, frozen=True)
class RawRow:
    """Una fila tal cual viene en el CSV, salvo la fecha: siempre normalizada
    a dd/MM/yyyy (ver módulo) para que `normalize.py`/`archive.py` no tengan
    que conocer el formato de origen."""

    date_raw: str
    time_raw: str
    temperature_raw: str
    pressure_raw: str


@dataclass(slots=True)
class ReadReport:
    """Lo que se descubrió/descartó al leer un CSV, para que quien llame
    pueda avisarlo en su log con su propio logger y ámbito. Se construye
    vacío y `read_raw_rows` lo rellena -delimitador/codificación no se saben
    hasta que se leen-."""

    delimiter: str = ""
    encoding: str = ""
    rejected: int = 0
    rejected_samples: list[str] = field(default_factory=list)

    @property
    def is_default_format(self) -> bool:
        return self.delimiter == "\t" and self.encoding == ENCODING


def detect_delimiter(path: Path) -> str:
    encoding = _detect_encoding(path, fallback=ENCODING)
    primera_linea = path.open(encoding=encoding).readline()
    return _detect_delimiter(primera_linea, _DELIMITERS)


def _fecha_a_dmy(date_raw: str) -> str | None:
    """Normaliza `date_raw` a "dd/MM/yyyy" si viene en ese formato (con o sin
    hora pegada). Cualquier otra cosa -incluida una fecha con pinta de
    ISO- devuelve None: no se adivina nada, se rechaza la fila (ver docstring
    del módulo)."""
    m = _FECHA_DMY_RE.match(date_raw)
    if not m:
        return None
    dia, mes, anio = m.groups()
    return f"{int(dia):02d}/{int(mes):02d}/{anio}"


def read_raw_rows(path: Path, report: ReadReport | None = None) -> list[RawRow]:
    """Lee el CSV entero: detecta codificación y separador, salta las dos
    cabeceras y devuelve las cuatro columnas de cada fila, como texto -con la
    fecha ya normalizada a dd/MM/yyyy-.

    Las filas cuya fecha no se puede interpretar se descartan (no todo el
    fichero) y se cuentan en `report` si se pasa uno."""
    encoding = _detect_encoding(path, fallback=ENCODING)
    with path.open(encoding=encoding) as head_f:
        delimiter = _detect_delimiter(head_f.readline(), _DELIMITERS)

    if report is not None:
        report.delimiter = delimiter
        report.encoding = encoding

    rows: list[RawRow] = []
    with path.open(newline="", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)
        next(reader, None)  # cabecera 1: miente sobre la columna de fecha
        next(reader, None)  # cabecera 2: formato real de cada columna
        for row in reader:
            if len(row) < 4:
                continue
            fecha = _fecha_a_dmy(row[0])
            if fecha is None:
                if report is not None:
                    report.rejected += 1
                    if len(report.rejected_samples) < 5:
                        report.rejected_samples.append(row[0])
                continue
            rows.append(RawRow(fecha, row[1], row[2], row[3]))
    return rows
