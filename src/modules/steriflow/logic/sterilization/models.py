"""Dato de esterilización de un ciclo de Steriflow.

De todas las fases que trae cada informe solo interesa la de esterilización
-la meseta-, que no siempre es la misma: `reader.py` explica cómo se localiza
y por qué. Si algo no se puede leer bien, el resto del ciclo se guarda igual y
se marca `needs_review` en vez de perderse.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(slots=True)
class SterilizationCycle:
    # Número real de la autoclave. Lo fija la configuración a partir de la
    # carpeta de la que salió el informe, no el PDF: la AUTOCLAVE8 imprime
    # "Cód. Autoclave 10" por un error histórico que ya no se puede corregir
    # en los informes emitidos (ver `logic/config.py:AutoclaveConfig`).
    autoclave_code: int
    started_at: dt.datetime
    source_filename: str
    source_sha256: str
    id: int | None = None
    # Nombre configurado de la autoclave ("AUTOCLAVE8"), que es como se
    # muestra y se filtra en la interfaz.
    autoclave: str = ""
    # El número que el informe imprime de sí mismo (10 en el caso de arriba).
    # Se guarda para poder auditar de dónde salió el dato y para detectar un
    # PDF traspapelado en la carpeta de otra máquina.
    reported_code: int | None = None
    cycle_number: str = ""
    product: str = ""
    batch: str = ""
    cycles_counter: int | None = None
    reported_at: dt.datetime | None = None

    # Qué fase del informe se ha leído como esterilización, tal y como la
    # numera y la nombra la máquina. Cambia con el programa (ver `reader.py`),
    # así que sin esto no se puede revisar un ciclo dudoso sin reabrir el PDF.
    sterilization_phase_number: int | None = None
    sterilization_phase_type: str = ""

    sterilization_start_ts: dt.datetime | None = None
    sterilization_end_ts: dt.datetime | None = None
    sterilization_duration_s: int | None = None
    sterilization_temp_end_c: float | None = None
    sterilization_temp_mean_c: float | None = None
    sterilization_temp_min_c: float | None = None
    sterilization_temp_max_c: float | None = None

    needs_review: bool = False
    review_notes: str = ""
