"""Etapa 3c - Metricas de la fase de esterilizacion.

`mean_temperature_c` es la media OFICIAL y cubre la fase completa, sobreimpulso
incluido: el sobreimpulso es real, no un artefacto.

`mean_stable_temperature_c` es la media que excluye la ventana de
estabilizacion. Sobre los datos reales la diferencia entre ambas es de ~0,10 °C
en Ferlo1-4 y de 0,01 °C en Ferlo5, cuyo sobreimpulso es mucho menor. Desde la
Fase 2 del port (D6) las dos son ademas las que decide validate.py: un ciclo
solo es conforme si ninguna de las dos baja de consigna.

F0 y VP (letalidad) no se portan: quedan fuera del calculo, del esquema y de
la interfaz hasta que se pidan (ver `legacy/sterilization_analysis/src/steril/
analysis/metrics.py` mientras ese repo exista).
"""

from __future__ import annotations

from ..config import Settings
from .coverage import phase_coverage
from .models import CycleResult, Phase, Series


def compute_metrics(
    serie: Series,
    cycle: CycleResult,
    settings: Settings,
) -> None:
    """Rellena las metricas de `cycle` in situ."""
    fase = cycle.phases.get(Phase.STERILIZATION)
    if fase is None:
        return

    consigna = cycle.evaluation_setpoint_c
    ventana_s = float(settings.sterilization_phase["stabilization_window_min"]) * 60.0
    a, b = fase.start_index, fase.end_index
    ts = serie.ts
    temps = serie.temperature_c
    nominal_s = float(settings.sampling["nominal_sample_interval_s"])
    dt_tope_s = nominal_s * 2.0

    cycle.mean_temperature_c = fase.mean_temperature_c
    cycle.temperature_min_c = fase.temperature_min_c
    cycle.temperature_max_c = fase.temperature_max_c

    estables = [temps[i] for i in range(a, b + 1)
                if temps[i] is not None
                and (ts[i] - ts[a]).total_seconds() >= ventana_s]
    cycle.mean_stable_temperature_c = (
        sum(estables) / len(estables) if estables else None
    )

    if consigna is not None:
        cycle.time_below_setpoint_min = _tiempo_bajo(serie, a, b, consigna, dt_tope_s)

    if cycle.target_time_min is not None:
        desviacion = fase.duration_min - cycle.target_time_min
        cycle.time_deviation_min = desviacion
        cycle.extra_time_min = max(desviacion, 0.0)

    cobertura = phase_coverage(serie, a, b, nominal_s)
    cycle.coverage_pct = cobertura.pct
    cycle.max_blind_window_s = cobertura.largest_blind_s
    cycle.uncovered_min = cobertura.uncovered_min


def _tiempo_bajo(serie: Series, a: int, b: int, consigna: float, dt_cap_s: float) -> float:
    """Minutos acumulados por debajo de la consigna dentro de la fase.

    Se calcula y se muestra, pero no decide el veredicto por si solo (ver
    validate.py): detecta los bajones que la media esconde.
    """
    total = 0.0
    for i in range(a, b):
        v = serie.temperature_c[i]
        if v is not None and v < consigna:
            delta = min((serie.ts[i + 1] - serie.ts[i]).total_seconds(), dt_cap_s)
            total += delta
    return total / 60.0
