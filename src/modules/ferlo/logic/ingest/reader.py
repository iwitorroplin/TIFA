"""Etapa 1 - Lectura del CSV de Ferlo, tal cual.

Portado de `legacy/sterilization_data_ferlo/src/importer.py`. Cuatro columnas
por POSICION, no por nombre: la primera cabecera del CSV rotula la columna de
fecha como "Hora" -solo la segunda cabecera dice el formato real-, así que
fiarse del nombre de columna cruzaría fecha y hora en los 80 ficheros a la
vez (ver invariantes de la Fase 0). cp1252 y no UTF-8 porque la cabecera trae
"M-0C" -un "°C" mal codificado por el equipo-.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

ENCODING = "cp1252"
_DELIMITERS = ("\t", ";", ",", "|")


@dataclass(slots=True, frozen=True)
class RawRow:
    """Una fila tal cual viene en el CSV. Nada se ha interpretado todavía."""

    date_raw: str
    time_raw: str
    temperature_raw: str
    pressure_raw: str


def detect_delimiter(path: Path) -> str:
    primera_linea = path.open(encoding=ENCODING).readline()
    for delim in _DELIMITERS:
        if delim in primera_linea:
            return delim
    return _DELIMITERS[0]  # tabulador por defecto


def read_raw_rows(path: Path) -> list[RawRow]:
    """Lee el CSV entero: detecta el separador, salta las dos cabeceras y
    devuelve las cuatro columnas de cada fila, como texto."""
    delimiter = detect_delimiter(path)
    with path.open(newline="", encoding=ENCODING) as f:
        reader = csv.reader(f, delimiter=delimiter)
        next(reader, None)  # cabecera 1: miente sobre la columna de fecha
        next(reader, None)  # cabecera 2: formato real de cada columna
        return [
            RawRow(row[0], row[1], row[2], row[3])
            for row in reader
            if len(row) >= 4
        ]
