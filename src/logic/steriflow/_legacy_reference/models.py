"""Modelos de Steriflow.

Nomenclatura igual que en `core.models`: ingles, snake_case y sufijo de unidad
(_c, _s). Ningun modulo de este paquete importa Qt salvo los de `ui/`.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

# La maquina numera las fases y las etiqueta por tipo ("Calentam.",
# "Enfriamiento 1", "Forced cool. 1"), pero NO marca cual es la de
# esterilizacion: en los ciclos de los autoclaves 6-9 la meseta es la fase 3, y
# la maquina la etiqueta "Calentam." igual que las dos rampas anteriores. Por
# eso el numero es fijo aqui y no una regla derivada del tipo.
STERILIZATION_PHASE_NUMBER = 3


@dataclass(slots=True)
class SteriflowPhase:
    """Una fila de la tabla HISTORIAL MEDIDAS del informe.

    Los valores son los que imprime la maquina, no recalculados: su min/max sale
    de su muestreo interno, mas fino que los 30 s de la seccion LISTA DE DATOS.
    """

    number: int
    type_name: str
    start_ts: dt.datetime
    end_ts: dt.datetime
    duration_s: int
    temperature_end_c: float | None = None
    temperature_mean_c: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None

    @property
    def duration_min(self) -> float:
        return self.duration_s / 60.0


@dataclass(slots=True)
class SteriflowCycle:
    """Un informe PDF completo: en Steriflow, un fichero es exactamente un ciclo.

    `started_at` sale del corchete de la cabecera ('[01/06/2026 01:01:20]') y es
    la identidad del ciclo junto al codigo de autoclave. La hora de arranque del
    ciclo es anterior a la de la fase 1 -la maquina cuenta desde el "Start
    Cycle", con el agua y las purgas previas-.
    """

    autoclave_code: int
    started_at: dt.datetime
    source_filename: str
    source_sha256: str
    batch: str = ""
    cycle_number: str = ""
    product: str = ""
    reported_at: dt.datetime | None = None
    cycles_counter: int | None = None
    phases: list[SteriflowPhase] = field(default_factory=list)

    @property
    def sterilization(self) -> SteriflowPhase | None:
        return next(
            (p for p in self.phases if p.number == STERILIZATION_PHASE_NUMBER), None
        )

    @property
    def end_ts(self) -> dt.datetime | None:
        return self.phases[-1].end_ts if self.phases else None
