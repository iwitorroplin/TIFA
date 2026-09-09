"""Cobertura de datos dentro de una fase.

Antes de esto, una sonda caida a mitad de ciclo daba veredictos opuestos segun
como lo escribiera el fichero de origen: celdas vacias (fila presente,
temperatura None) hacia crecer `missing_temperature` pero un hueco de filas
ausentes (el reloj salta sin que exista la fila) solo generaba `data_gap` -dos
codigos con umbrales distintos para el mismo fallo fisico-. Aqui se tratan por
igual: un segmento (i, i+1) solo cuenta como "observado" si las dos muestras
tienen valor Y el salto de tiempo entre ellas no excede el margen de huecos, de
modo que da igual si el hueco viene de una celda vacia o de una fila que no
llego a escribirse.

`coverage_pct`/`max_blind_window_s` se calculan siempre (ver metrics.py), pero
no deciden el veredicto por si solos -ver validate.py-.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .models import Series


@dataclass(slots=True)
class BlindWindow:
    """Tramo de tiempo, dentro de la fase, sin ninguna lectura de fiar."""

    start_ts: dt.datetime
    end_ts: dt.datetime

    @property
    def duration_s(self) -> float:
        return (self.end_ts - self.start_ts).total_seconds()


@dataclass(slots=True)
class Coverage:
    """Cobertura de una fase: cuanto de su duracion esta respaldado por datos."""

    expected_s: float
    observed_s: float
    blind_windows: list[BlindWindow] = field(default_factory=list)

    @property
    def uncovered_s(self) -> float:
        return max(self.expected_s - self.observed_s, 0.0)

    @property
    def uncovered_min(self) -> float:
        return self.uncovered_s / 60.0

    @property
    def pct(self) -> float:
        """Porcentaje observado. 100.0 si la fase no tiene duracion (caso degenerado)."""
        if self.expected_s <= 0:
            return 100.0
        return 100.0 * self.observed_s / self.expected_s

    @property
    def largest_blind_s(self) -> float:
        return max((w.duration_s for w in self.blind_windows), default=0.0)


def phase_coverage(
    serie: Series,
    a: int,
    b: int,
    nominal_sample_interval_s: float,
    *,
    gap_factor: float = 1.5,
) -> Coverage:
    """Cobertura de datos entre los indices `a` y `b` (inclusive), ambos extremos.

    Un segmento (i, i+1) cuenta como observado solo si las dos muestras tienen
    valor y el salto de tiempo no excede `nominal_sample_interval_s * gap_factor`.
    Cualquier otro caso —valor ausente en un extremo, o salto de tiempo mayor
    porque faltan filas enteras— se acumula como tramo ciego contiguo.
    """
    ts = serie.ts
    temps = serie.temperature_c
    expected_s = (ts[b] - ts[a]).total_seconds()
    umbral = nominal_sample_interval_s * gap_factor

    observed_s = 0.0
    blind_windows: list[BlindWindow] = []
    hueco_inicio: dt.datetime | None = None

    for i in range(a, b):
        delta = (ts[i + 1] - ts[i]).total_seconds()
        segmento_valido = (
            temps[i] is not None and temps[i + 1] is not None and delta <= umbral
        )
        if segmento_valido:
            observed_s += delta
            if hueco_inicio is not None:
                blind_windows.append(BlindWindow(hueco_inicio, ts[i]))
                hueco_inicio = None
        elif hueco_inicio is None:
            hueco_inicio = ts[i]

    if hueco_inicio is not None:
        blind_windows.append(BlindWindow(hueco_inicio, ts[b]))

    return Coverage(expected_s=expected_s, observed_s=observed_s, blind_windows=blind_windows)
