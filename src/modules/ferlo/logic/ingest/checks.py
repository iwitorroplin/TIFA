"""Etapa de verificación: corre en cada importación (a diferencia del origen,
donde era un script que había que acordarse de lanzar a mano), y vuelca su
resumen al log del módulo -ver `logic/ingest/service.py`-. Solo lectura sobre
lo que se acaba de leer, no modifica nada.

Portado de `legacy/sterilization_data_ferlo/src/checker.py`, adaptado de
consultas SQL sobre `measurements_raw` a un recorrido en memoria sobre las
`RawRow` recién leídas: es justo la fase que descubre que '<<<<<<<<' existe,
antes de que la normalización tenga que decidir qué hacer con él.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .reader import RawRow

_DECIMAL_RE = re.compile(r"^\d+,\d+$")
_ENTERO_RE = re.compile(r"^\d+$")

_CATEGORIAS = (
    "decimal_positivo", "decimal_negativo",
    "entero_positivo", "entero_negativo",
    "vacio", "otro",
)


def classify(value: str | None) -> str:
    if value is None or value == "":
        return "vacio"
    if _DECIMAL_RE.match(value):
        return "decimal_positivo"
    if value.startswith("-") and _DECIMAL_RE.match(value[1:]):
        return "decimal_negativo"
    if _ENTERO_RE.match(value):
        return "entero_positivo"
    if value.startswith("-") and _ENTERO_RE.match(value[1:]):
        return "entero_negativo"
    return "otro"


@dataclass(slots=True)
class ColumnPatterns:
    counts: dict[str, int] = field(default_factory=dict)
    otros: Counter = field(default_factory=Counter)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def value_patterns(rows: list[RawRow], column: str) -> ColumnPatterns:
    """Clasifica `temperature_raw`/`pressure_raw` de `rows` en las categorías
    de `classify`, y lista los valores 'otro' que aparecen -es la señal de un
    formato nuevo que la normalización todavía no sabe interpretar-."""
    resultado = ColumnPatterns()
    for row in rows:
        valor = getattr(row, column)
        categoria = classify(valor)
        resultado.counts[categoria] = resultado.counts.get(categoria, 0) + 1
        if categoria == "otro":
            resultado.otros[valor] += 1
    return resultado


@dataclass(slots=True)
class CheckSummary:
    rows: int
    temperature: ColumnPatterns
    pressure: ColumnPatterns

    @property
    def cuadra(self) -> bool:
        """Si las categorías suman el total, no hay ningún patrón sin
        clasificar escondido en 'otro' de forma inconsistente."""
        return self.temperature.total == self.rows and self.pressure.total == self.rows

    def resumen_texto(self) -> str:
        partes = [f"{self.rows} filas"]
        for nombre, patrones in (("TEMP", self.temperature), ("PRES", self.pressure)):
            otros = sum(patrones.otros.values())
            partes.append(f"{nombre}: {patrones.counts.get('vacio', 0)} vacías"
                          + (f", {otros} sin clasificar" if otros else ""))
        return " · ".join(partes)


def check_rows(rows: list[RawRow]) -> CheckSummary:
    return CheckSummary(
        rows=len(rows),
        temperature=value_patterns(rows, "temperature_raw"),
        pressure=value_patterns(rows, "pressure_raw"),
    )
