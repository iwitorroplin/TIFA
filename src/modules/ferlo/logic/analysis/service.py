"""Orquesta segmentar -> evaluar sobre una serie ya normalizada.

Deliberadamente no lee ficheros ni escribe en base de datos: eso depende de
`logic/ingest/` (Fase 1) y de `logic/schema.py` (Fase 3), que todavia no
existen. Este modulo es el unico punto que la UI necesitara llamar para la
parte de calculo. No importa Qt, igual que el resto de `logic/analysis/`.
"""

from __future__ import annotations

from ..config import Settings
from .metrics import compute_metrics
from .models import CycleResult, Series, SterilizationProgram
from .phases import detect_phases
from .segment import segment
from .validate import validate


def analyze_series(
    serie: Series,
    settings: Settings,
    program: SterilizationProgram | None = None,
) -> list[CycleResult]:
    cycles = segment(serie, settings)
    for cycle in cycles:
        assign(serie, cycle, settings, program)
    return cycles


def assign(
    serie: Series,
    cycle: CycleResult,
    settings: Settings,
    program: SterilizationProgram | None,
) -> CycleResult:
    """Evalua un ciclo, con o sin programa asignado.

    Sin programa se usa la consigna medida, de modo que las fases y las metricas
    puedan verse antes de asignar; el estado queda en UNASSIGNED y no se emite
    ningun veredicto de conformidad.
    """
    if program is not None:
        cycle.program_code = program.code
        cycle.target_temperature_c = program.target_temperature_c
        cycle.target_time_min = program.target_time_min
        cycle.evaluation_setpoint_c = program.target_temperature_c
    else:
        cycle.program_code = None
        cycle.target_temperature_c = None
        cycle.target_time_min = None
        cycle.evaluation_setpoint_c = cycle.measured_setpoint_c

    cycle.findings.clear()
    cycle.phases, dips = detect_phases(
        serie, cycle, cycle.evaluation_setpoint_c, settings
    )
    compute_metrics(serie, cycle, settings)
    validate(serie, cycle, settings, dips)
    return cycle
