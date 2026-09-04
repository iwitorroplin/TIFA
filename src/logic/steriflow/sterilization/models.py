"""Dato de esterilización (fase 3) de un ciclo de Steriflow.

Solo la fase 3 -esterilización- de las seis que trae cada informe interesa;
ver `reader.py` para el porqué. Si algo no se puede leer bien, el resto del
ciclo se guarda igual y se marca `needs_review` en vez de perderse.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(slots=True)
class SterilizationCycle:
    autoclave_code: int
    started_at: dt.datetime
    source_filename: str
    source_sha256: str
    id: int | None = None
    cycle_number: str = ""
    product: str = ""
    batch: str = ""
    cycles_counter: int | None = None
    reported_at: dt.datetime | None = None

    sterilization_start_ts: dt.datetime | None = None
    sterilization_end_ts: dt.datetime | None = None
    sterilization_duration_s: int | None = None
    sterilization_temp_end_c: float | None = None
    sterilization_temp_mean_c: float | None = None
    sterilization_temp_min_c: float | None = None
    sterilization_temp_max_c: float | None = None

    needs_review: bool = False
    review_notes: str = ""
