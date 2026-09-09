"""Etapa 3c - Metricas de la fase de esterilizacion.

`mean_temperature_c` es la media OFICIAL y cubre la fase completa, sobreimpulso
incluido: el sobreimpulso es real, no un artefacto.

`mean_stable_temperature_c` es informativa y excluye la ventana de
estabilizacion. Sobre los datos reales la diferencia entre ambas es de ~0,10 °C
en Ferlo1-4 y de 0,01 °C en Ferlo5, cuyo sobreimpulso es mucho menor.

Todas las integrales (F0, VP, tiempo bajo consigna) topan el `dt` entre dos
muestras a `nominal_sample_interval_s * 2`: sin ese tope, un hueco de filas
ausentes de 20 minutos con la ultima lectura buena a 117 °C acreditaba 20
minutos de letalidad sin haber observado nada en ese tramo (ver
`analysis/coverage.py` para la misma correccion aplicada a la cobertura).
"""

from __future__ import annotations

from ..core.config import Settings
from ..core.enums import Phase
from ..core.models import CycleResult, Series
from .coverage import phase_coverage


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

    let = settings.lethality
    if let.get("enabled", True):
        cycle.lethality_f0_min = lethality(
            serie, a, b,
            reference_temperature_c=float(let["reference_temperature_c"]),
            z_value_c=float(let["z_value_c"]),
            dt_cap_s=dt_tope_s,
        )
    if let.get("vp_enabled", True):
        cycle.lethality_vp_min = lethality(
            serie, a, b,
            reference_temperature_c=float(let["vp_reference_temperature_c"]),
            z_value_c=float(let["vp_z_value_c"]),
            dt_cap_s=dt_tope_s,
        )


def _tiempo_bajo(serie: Series, a: int, b: int, consigna: float, dt_cap_s: float) -> float:
    """Minutos acumulados por debajo de la consigna dentro de la fase.

    Vale mas que F0 para el uso real: detecta los bajones que la media esconde,
    sin ninguna de sus pegas.
    """
    total = 0.0
    for i in range(a, b):
        v = serie.temperature_c[i]
        if v is not None and v < consigna:
            delta = min((serie.ts[i + 1] - serie.ts[i]).total_seconds(), dt_cap_s)
            total += delta
    return total / 60.0


def lethality(
    serie: Series,
    a: int,
    b: int,
    *,
    reference_temperature_c: float,
    z_value_c: float,
    dt_cap_s: float | None = None,
) -> float:
    """Letalidad = suma de 10^((T - Tref)/z) * dt, en minutos.

    Generico: con `reference_temperature_c=121.1` (referencia por defecto de
    `lethality_f0`) da F0; con `93.3` (referencia de vapor de agua a 1 atm,
    norma ISO 11138-1:2017) da VP. En ambos casos es orientativo -se calcula
    sobre el sensor de camara, no el punto frio del producto- y no es criterio
    de aceptacion.

    `dt_cap_s`, si se indica, topa el intervalo entre dos muestras: sin tope,
    un hueco de filas ausentes acredita letalidad por todo el tiempo sin datos.
    """
    total = 0.0
    for i in range(a, b):
        v = serie.temperature_c[i]
        if v is None:
            continue
        delta_s = (serie.ts[i + 1] - serie.ts[i]).total_seconds()
        if dt_cap_s is not None:
            delta_s = min(delta_s, dt_cap_s)
        dt_min = delta_s / 60.0
        total += 10.0 ** ((v - reference_temperature_c) / z_value_c) * dt_min
    return total


def lethality_f0(
    serie: Series,
    a: int,
    b: int,
    *,
    reference_temperature_c: float = 121.1,
    z_value_c: float = 10.0,
    dt_cap_s: float | None = None,
) -> float:
    """F0, en minutos. Envoltorio de `lethality()` con la referencia de F0."""
    return lethality(
        serie, a, b,
        reference_temperature_c=reference_temperature_c, z_value_c=z_value_c,
        dt_cap_s=dt_cap_s,
    )


def lethality_vp(
    serie: Series,
    a: int,
    b: int,
    *,
    reference_temperature_c: float = 93.3,
    z_value_c: float = 10.0,
    dt_cap_s: float | None = None,
) -> float:
    """VP_93, en minutos. Envoltorio de `lethality()` con la referencia de vapor
    de agua a 93,3 °C (1 atm, ISO 11138-1:2017). ORIENTATIVO, ver docstring de
    `lethality()`."""
    return lethality(
        serie, a, b,
        reference_temperature_c=reference_temperature_c, z_value_c=z_value_c,
        dt_cap_s=dt_cap_s,
    )
