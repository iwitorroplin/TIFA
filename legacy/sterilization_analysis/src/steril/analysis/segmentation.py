"""Etapa 3a - Segmentacion, agnostica del programa.

No sabe nada de los programas de consigna: solo geometria de la curva. Es lo que
rompe la circularidad del planteamiento inicial (las fases se definian a partir
de la consigna del programa, pero el programa se asigna despues de ver donde
esta cada ciclo).

La consigna se estima por MODA, no por el maximo. Los autoclaves sobreimpulsan
sistematicamente al final de la rampa -Ferlo1 sube a 121,3 °C durante 4 minutos
antes de estabilizarse en 117,1- asi que el pico no es la meseta. En un ciclo
real hay 844 muestras entre 117 y 118 °C frente a 4 entre 121 y 122.
"""

from __future__ import annotations

from collections import Counter

from ..core.config import Settings
from ..core.enums import CycleStatus
from ..core.models import CycleResult, Series


def segment(serie: Series, settings: Settings) -> list[CycleResult]:
    """Detecta los ciclos de una serie sin conocer el programa."""
    cfg = settings.cycle_detection
    t_inicio = float(cfg["cycle_start_temperature_c"])
    t_fin = float(cfg["cycle_end_temperature_c"])
    dur_min_s = float(cfg["min_cycle_duration_min"]) * 60.0
    pico_min = float(cfg["min_cycle_peak_temperature_c"])
    paso = float(cfg["setpoint_mode_bin_c"])
    suelo = float(cfg["setpoint_mode_floor_c"])

    temps = serie.temperature_c
    n = len(temps)
    ciclos: list[CycleResult] = []
    dentro = False
    inicio = 0

    for i, v in enumerate(temps):
        if v is None:
            continue
        if not dentro and v >= t_inicio:
            dentro, inicio = True, i
        elif dentro and v < t_fin:
            ciclos.append(_construir(serie, inicio, i, paso, suelo))
            dentro = False
    if dentro:
        ciclo = _construir(serie, inicio, n - 1, paso, suelo)
        ciclo.status = CycleStatus.INCOMPLETE  # el fichero acaba a mitad de ciclo
        ciclos.append(ciclo)

    return [
        c for c in ciclos
        if c.peak_temperature_c >= pico_min
        and (c.end_ts - c.start_ts).total_seconds() >= dur_min_s
    ]


def _construir(
    serie: Series, inicio: int, fin: int, paso: float, suelo: float
) -> CycleResult:
    validos = [serie.temperature_c[i] for i in range(inicio, fin + 1)
               if serie.temperature_c[i] is not None]
    pico = max(validos) if validos else 0.0
    return CycleResult(
        autoclave_id=serie.autoclave_id,
        autoclave_name=serie.autoclave_name,
        start_index=inicio,
        end_index=fin,
        start_ts=serie.ts[inicio],
        end_ts=serie.ts[fin],
        peak_temperature_c=pico,
        measured_setpoint_c=estimate_setpoint(validos, paso, suelo),
    )


def estimate_setpoint(temperaturas: list[float], paso: float, suelo: float) -> float:
    """Consigna estimada = moda de la meseta.

    Se redondea a `paso` (decimas) y se ignoran las muestras por debajo de
    `suelo`, que son rampa y enfriamiento. El resultado se devuelve al entero
    mas proximo porque las consignas de los programas son enteras.
    """
    altas = [t for t in temperaturas if t >= suelo]
    if not altas:
        return 0.0
    escala = 1.0 / paso
    moda, _ = Counter(round(t * escala) / escala for t in altas).most_common(1)[0]
    return float(round(moda))
