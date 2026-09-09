"""Utilidades para construir series sinteticas.

Los casos raros -sobreimpulso, oscilacion en la estabilizacion, ciclo corto,
hueco dentro de la meseta- se prueban con curvas generadas, no esperando a
encontrarlos en produccion. Portado (Fase 2) desde
`legacy/sterilization_analysis/tests/conftest.py`; aqui se le quita ademas la
fixture `autoclave`, que ya no hace falta -`Autoclave` es cosa de
`logic/ingest/` (Fase 1), no de `logic/analysis/`-.
"""

from __future__ import annotations

import copy
import datetime as dt

import pytest

from src.modules.ferlo.logic.config import DEFAULT_SETTINGS, Settings
from src.modules.ferlo.logic.analysis.models import Series

INICIO = dt.datetime(2026, 7, 31, 6, 0, 0)


@pytest.fixture
def settings() -> Settings:
    return Settings(copy.deepcopy(DEFAULT_SETTINGS))


def build_series(
    temperaturas: list[float | None],
    *,
    interval_s: int = 5,
    inicio: dt.datetime = INICIO,
) -> Series:
    serie = Series(autoclave_id=1, autoclave_name="Test", source_filename="test.xlsx")
    for i, t in enumerate(temperaturas):
        serie.ts.append(inicio + dt.timedelta(seconds=i * interval_s))
        serie.temperature_c.append(t)
        serie.pressure_bar.append(0.0)
    return serie


def build_series_con_hueco(
    temperaturas: list[float],
    *,
    desde_min: float,
    duracion_min: float,
    modo: str,
    interval_s: int = 5,
    inicio: dt.datetime = INICIO,
) -> Series:
    """Como `build_series`, pero simulando un fallo de sonda de `duracion_min`
    minutos empezando en el minuto `desde_min`.

    Los dos modos son el mismo fallo fisico escrito de dos maneras distintas
    -y por eso deben producir la misma cobertura y el mismo veredicto (ver
    `analysis/coverage.py`)-:

      * "celdas_vacias": las filas siguen existiendo, con temperatura None.
      * "filas_ausentes": esas filas no llegan a escribirse -el reloj salta-,
        igual que un hueco de datos real en el fichero de origen.
    """
    indice_inicio = int(desde_min * 60 / interval_s)
    n = int(duracion_min * 60 / interval_s)
    serie = Series(autoclave_id=1, autoclave_name="Test", source_filename="test.xlsx")
    for i, t in enumerate(temperaturas):
        en_hueco = indice_inicio <= i < indice_inicio + n
        if en_hueco and modo == "filas_ausentes":
            continue
        serie.ts.append(inicio + dt.timedelta(seconds=i * interval_s))
        serie.temperature_c.append(None if (en_hueco and modo == "celdas_vacias") else t)
        serie.pressure_bar.append(0.0)
    return serie


def rampa(desde: float, hasta: float, muestras: int) -> list[float]:
    if muestras <= 1:
        return [hasta]
    paso = (hasta - desde) / (muestras - 1)
    return [desde + paso * i for i in range(muestras)]


def meseta(valor: float, minutos: float, *, interval_s: int = 5) -> list[float]:
    return [valor] * int(minutos * 60 / interval_s)


def ciclo_tipico(
    *,
    consigna: float = 117.0,
    minutos_meseta: float = 73.0,
    sobreimpulso: float = 121.3,
    minutos_sobreimpulso: float = 4.0,
    interval_s: int = 5,
) -> list[float]:
    """Reproduce la forma real: rampa, sobreimpulso, meseta, enfriamiento.

    El sobreimpulso es lo que hace que estimar la consigna por el maximo falle:
    el pico esta 4 °C por encima de la meseta.

    OJO: la fase de esterilizacion resultante dura mas que `minutos_meseta`,
    porque empieza al cruzar la banda -durante la rampa- y el sobreimpulso cae
    dentro. Para probar umbrales de tiempo o de temperatura usa `ciclo_plano`.
    """
    n_over = int(minutos_sobreimpulso * 60 / interval_s)
    return (
        rampa(40.0, sobreimpulso, int(10 * 60 / interval_s))
        + rampa(sobreimpulso, consigna, n_over)
        + meseta(consigna, minutos_meseta, interval_s=interval_s)
        + rampa(consigna, 40.0, int(12 * 60 / interval_s))
    )


def ciclo_plano(
    *,
    consigna: float = 117.0,
    minutos_meseta: float = 73.0,
    interval_s: int = 5,
) -> list[float]:
    """Ciclo sin sobreimpulso apreciable.

    La fase de esterilizacion coincide con la meseta, asi que los umbrales de
    tiempo y temperatura se pueden comprobar sin que el sobreimpulso desplace
    los numeros.
    """
    return ciclo_tipico(
        consigna=consigna,
        minutos_meseta=minutos_meseta,
        sobreimpulso=consigna + 0.2,
        minutos_sobreimpulso=0.2,
        interval_s=interval_s,
    )
