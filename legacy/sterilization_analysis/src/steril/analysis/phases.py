"""Etapa 3b - Fases, ya con la consigna conocida.

La fase de esterilizacion entra y sale en `consigna - sterilization_tolerance_c`,
pero la salida lleva antirrebote: una bajada solo termina la fase si persiste
mas de `exit_debounce_s`.

Sin ese antirrebote el resultado es absurdo con datos reales. Ferlo5 oscila
durante la estabilizacion y baja de la banda a los 65 segundos de entrar; con la
regla literal "termina al bajar de la banda" sus ciclos durarian 65 segundos en
lugar de los 75 minutos que duran. Las bajadas absorbidas no se pierden: se
devuelven para que se marquen como revision manual.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from ..core.config import Settings
from ..core.enums import Phase
from ..core.models import CycleResult, PhaseResult, Series


@dataclass(slots=True)
class Dip:
    """Bajada bajo la banda absorbida por el antirrebote."""

    start_ts: dt.datetime
    end_ts: dt.datetime
    min_temperature_c: float

    @property
    def duration_s(self) -> float:
        return (self.end_ts - self.start_ts).total_seconds()


def detect_phases(
    serie: Series,
    cycle: CycleResult,
    target_temperature_c: float,
    settings: Settings,
) -> tuple[dict[Phase, PhaseResult], list[Dip]]:
    cfg = settings.sterilization_phase
    banda = target_temperature_c - float(cfg["sterilization_tolerance_c"])
    debounce = float(cfg["exit_debounce_s"])

    temps = serie.temperature_c
    ts = serie.ts
    a, b = cycle.start_index, cycle.end_index

    entrada = next(
        (i for i in range(a, b + 1) if temps[i] is not None and temps[i] >= banda),
        None,
    )
    if entrada is None:
        return {}, []

    salida = entrada
    dips: list[Dip] = []
    bajada_desde: int | None = None
    consolidada = False

    for i in range(entrada, b + 1):
        v = temps[i]
        if v is None:
            continue
        if v >= banda:
            if bajada_desde is not None:
                dips.append(_dip(serie, bajada_desde, i))
                bajada_desde = None
            salida = i
        else:
            if bajada_desde is None:
                bajada_desde = i
            elif (ts[i] - ts[bajada_desde]).total_seconds() > debounce:
                consolidada = True
                break  # la bajada persiste: la fase ha terminado de verdad

    # Una bajada consolidada NO es un dip: es el final real de la fase, casi
    # siempre el enfriamiento. Solo se registra la que segui­a abierta sin haber
    # llegado a superar el antirrebote cuando se acabo el ciclo.
    if bajada_desde is not None and not consolidada:
        dips.append(_dip(serie, bajada_desde, min(b, len(ts) - 1)))

    fases: dict[Phase, PhaseResult] = {
        Phase.STERILIZATION: _phase(serie, Phase.STERILIZATION, entrada, salida)
    }
    if entrada > a:
        fases[Phase.HEATING] = _phase(serie, Phase.HEATING, a, entrada)
    if salida < b:
        fases[Phase.COOLING] = _phase(serie, Phase.COOLING, salida, b)
    return fases, dips


def _dip(serie: Series, inicio: int, regreso: int) -> Dip:
    """`regreso` es el indice de la primera muestra que vuelve a la banda.

    La duracion se mide hasta ese regreso, que es el instante en que la
    temperatura deja de estar por debajo; asi no hay que suponer el intervalo
    de muestreo.
    """
    valores = [serie.temperature_c[i] for i in range(inicio, regreso)
               if serie.temperature_c[i] is not None]
    return Dip(
        start_ts=serie.ts[inicio],
        end_ts=serie.ts[min(regreso, len(serie.ts) - 1)],
        min_temperature_c=min(valores) if valores else float("nan"),
    )


def _phase(serie: Series, phase: Phase, inicio: int, fin: int) -> PhaseResult:
    valores = [serie.temperature_c[i] for i in range(inicio, fin + 1)
               if serie.temperature_c[i] is not None]
    return PhaseResult(
        phase=phase,
        start_index=inicio,
        end_index=fin,
        start_ts=serie.ts[inicio],
        end_ts=serie.ts[fin],
        mean_temperature_c=sum(valores) / len(valores) if valores else None,
        temperature_min_c=min(valores) if valores else None,
        temperature_max_c=max(valores) if valores else None,
    )
