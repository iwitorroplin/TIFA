"""Qué columnas tiene la tabla de ciclos de esterilización: clave, cabecera,
si son fijas o configurables, alineación de impresión y cómo sacar el texto
de la celda a partir de un `SterilizationCycle`.

Fuente única para pantalla e impresión: `ui/data_page/data_page.py`/
`ui/data_page/data_view_model.py` filtran esta misma lista según la
configuración guardada (`logic/config.py:ColumnsConfig`), así que las dos
vistas nunca pueden mostrar un conjunto de columnas distinto sin que sea a
propósito.

`Align` es propio y no `src.shared.ui.printing.Align`: ese módulo importa
PySide6, y nada en `logic/` puede arrastrar Qt (ver `tests/test_architecture.py`)
aunque sea solo por un enum. `ui/data_page/print_job.py` traduce este `Align`
al de `printing` al construir el `PrintJob`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from src.modules.steriflow.logic.sterilization.models import SterilizationCycle
from src.shared.utils.formatting import MISSING, format_datetime, format_decimal, format_duration_hms


class Align(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


def autoclave_label(cycle: SterilizationCycle) -> str:
    """El nombre configurado de la máquina. Los ciclos guardados antes de
    que se guardara ese nombre solo tienen el número, así que se compone
    uno con la misma forma en vez de dejar la celda vacía."""
    return cycle.autoclave or f"AUTOCLAVE{cycle.autoclave_code}"


def phase_label(cycle: SterilizationCycle) -> str:
    """Qué fase del informe se leyó como esterilización. Cambia según el
    programa (ver `logic/sterilization/reader.py`), así que verla en la
    tabla es lo que permite revisar un ciclo raro sin abrir el PDF."""
    if cycle.sterilization_phase_number is None:
        return MISSING
    if not cycle.sterilization_phase_type:
        return str(cycle.sterilization_phase_number)
    return f"{cycle.sterilization_phase_number} · {cycle.sterilization_phase_type}"


@dataclass(frozen=True)
class CycleColumn:
    key: str
    header: str
    # True: siempre visible, sin checkbox en Configuración.
    fixed: bool
    align: Align
    cell: Callable[[SterilizationCycle], str]


CYCLE_COLUMNS: list[CycleColumn] = [
    CycleColumn("autoclave", "Autoclave", True, Align.LEFT,
                autoclave_label),
    CycleColumn("started_at", "Fecha inicio", False, Align.LEFT,
                lambda c: format_datetime(c.started_at)),
    CycleColumn("product", "Producto", True, Align.LEFT,
                lambda c: c.product),
    CycleColumn("cycle_number", "Nº ciclo", False, Align.RIGHT,
                lambda c: c.cycle_number),
    CycleColumn("phase", "Fase esterilización", False, Align.LEFT,
                phase_label),
    CycleColumn("duration", "Duración esterilización", True, Align.RIGHT,
                lambda c: format_duration_hms(c.sterilization_duration_s)),
    CycleColumn("sterilization_start_ts", "Ini. Esterilización", False, Align.LEFT,
                lambda c: format_datetime(c.sterilization_start_ts)),
    CycleColumn("sterilization_end_ts", "Fin Esterilización", False, Align.LEFT,
                lambda c: format_datetime(c.sterilization_end_ts)),
    CycleColumn("temp_mean", "T media (°C)", True, Align.RIGHT,
                lambda c: format_decimal(c.sterilization_temp_mean_c, 2)),
    CycleColumn("temp_min", "T mín (°C)", False, Align.RIGHT,
                lambda c: format_decimal(c.sterilization_temp_min_c, 2)),
    CycleColumn("temp_max", "T máx (°C)", False, Align.RIGHT,
                lambda c: format_decimal(c.sterilization_temp_max_c, 2)),
    # Variante de pantalla ("Revisar"/vacío); `print_cells` en el view model
    # sustituye esta única celda por las notas de revisión al imprimir, sin
    # que haga falta una segunda definición de columna aquí.
    CycleColumn("review", "Revisión", True, Align.LEFT,
                lambda c: "Revisar" if c.needs_review else ""),
]

CONFIGURABLE_COLUMN_KEYS: list[str] = [col.key for col in CYCLE_COLUMNS if not col.fixed]
