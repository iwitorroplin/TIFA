"""Qué columnas tiene la tabla de ciclos de esterilización: clave, cabecera,
si son fijas o configurables, alineación de impresión y cómo sacar el texto
de la celda a partir de un `SterilizationCycle`.

Fuente única para pantalla e impresión: `ui/data_page/data_page.py`/
`ui/data_page/data_presenter.py` filtran esta misma lista según la
configuración guardada (`logic/config.py:ColumnsConfig`), así que las dos
vistas nunca pueden mostrar un conjunto de columnas distinto sin que sea a
propósito.

`Align` es propio y no `src.shared.ui.printing.Align`: ese módulo importa
PySide6, y nada en `logic/` puede arrastrar Qt (ver `tests/test_architecture.py`)
aunque sea solo por un enum. `ui/data_page/print_job.py` traduce este `Align`
al de `printing` al construir el `PrintJob`.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable

from src.modules.steriflow.logic.sterilization.models import SterilizationCycle

if TYPE_CHECKING:
    from src.modules.steriflow.ui.data_page.data_presenter import SteriflowDataPresenter


class Align(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_temp(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _format_datetime(value: dt.datetime | None) -> str:
    return "—" if value is None else value.strftime("%d/%m/%Y %H:%M:%S")


@dataclass(frozen=True)
class CycleColumn:
    key: str
    header: str
    # True: siempre visible, sin checkbox en Configuración.
    fixed: bool
    align: Align
    cell: Callable[["SteriflowDataPresenter", SterilizationCycle], str]


CYCLE_COLUMNS: list[CycleColumn] = [
    CycleColumn("autoclave", "Autoclave", True, Align.LEFT,
                lambda p, c: p.autoclave_label(c)),
    CycleColumn("started_at", "Fecha inicio", False, Align.LEFT,
                lambda p, c: c.started_at.strftime("%d/%m/%Y %H:%M:%S")),
    CycleColumn("product", "Producto", True, Align.LEFT,
                lambda p, c: c.product),
    CycleColumn("cycle_number", "Nº ciclo", False, Align.RIGHT,
                lambda p, c: c.cycle_number),
    CycleColumn("phase", "Fase esterilización", False, Align.LEFT,
                lambda p, c: p.phase_label(c)),
    CycleColumn("duration", "Duración esterilización", True, Align.RIGHT,
                lambda p, c: _format_duration(c.sterilization_duration_s)),
    CycleColumn("sterilization_start_ts", "Ini. Esterilización", False, Align.LEFT,
                lambda p, c: _format_datetime(c.sterilization_start_ts)),
    CycleColumn("sterilization_end_ts", "Fin Esterilización", False, Align.LEFT,
                lambda p, c: _format_datetime(c.sterilization_end_ts)),
    CycleColumn("temp_mean", "T media (°C)", True, Align.RIGHT,
                lambda p, c: _format_temp(c.sterilization_temp_mean_c)),
    CycleColumn("temp_min", "T mín (°C)", False, Align.RIGHT,
                lambda p, c: _format_temp(c.sterilization_temp_min_c)),
    CycleColumn("temp_max", "T máx (°C)", False, Align.RIGHT,
                lambda p, c: _format_temp(c.sterilization_temp_max_c)),
    # Variante de pantalla ("Revisar"/vacío); `print_cells` en el presenter
    # sustituye esta única celda por las notas de revisión al imprimir, sin
    # que haga falta una segunda definición de columna aquí.
    CycleColumn("review", "Revisión", True, Align.LEFT,
                lambda p, c: "Revisar" if c.needs_review else ""),
]

CONFIGURABLE_COLUMN_KEYS: list[str] = [col.key for col in CYCLE_COLUMNS if not col.fixed]
