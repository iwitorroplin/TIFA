"""Regresion del defecto 4: una sonda caida a mitad de ciclo daba veredictos
opuestos segun como lo escribiera el fichero de origen -celdas vacias
(fila presente, temperatura None) frente a filas ausentes (el reloj salta)-.

`analysis/coverage.py` trata los dos casos igual. La version portada de este
fichero (Fase 2) pierde el test de F0 -`analysis/metrics.py` ya no calcula
letalidad, ver su docstring- pero conserva los que prueban la cobertura en si.
"""

from __future__ import annotations

from conftest import build_series_con_hueco, ciclo_plano

from src.modules.ferlo.logic.analysis.coverage import phase_coverage
from src.modules.ferlo.logic.analysis.models import Phase, SterilizationProgram
from src.modules.ferlo.logic.analysis.phases import detect_phases
from src.modules.ferlo.logic.analysis.segment import segment
from src.modules.ferlo.logic.analysis.service import assign

P117 = SterilizationProgram(code=1, target_temperature_c=117.0, target_time_min=73.0)


def _fase_esterilizacion(serie, settings):
    ciclo = segment(serie, settings)[0]
    fases, _ = detect_phases(serie, ciclo, ciclo.measured_setpoint_c, settings)
    return fases[Phase.STERILIZATION]


def test_celdas_vacias_y_filas_ausentes_dan_la_misma_cobertura(settings):
    base = ciclo_plano(consigna=117.0, minutos_meseta=73.0)
    nominal_s = settings.sampling["nominal_sample_interval_s"]

    coberturas = {}
    for modo in ("celdas_vacias", "filas_ausentes"):
        serie = build_series_con_hueco(
            base, desde_min=30.0, duracion_min=20.0, modo=modo,
        )
        fase = _fase_esterilizacion(serie, settings)
        coberturas[modo] = phase_coverage(serie, fase.start_index, fase.end_index, nominal_s)

    assert coberturas["celdas_vacias"].pct == coberturas["filas_ausentes"].pct
    assert coberturas["celdas_vacias"].largest_blind_s == coberturas["filas_ausentes"].largest_blind_s
    assert coberturas["celdas_vacias"].pct < 90.0  # el hueco es real: 20 de 73 min


def test_sin_hueco_la_cobertura_es_completa(settings):
    serie = build_series_con_hueco(
        ciclo_plano(), desde_min=1000.0, duracion_min=0.0, modo="celdas_vacias",
    )
    fase = _fase_esterilizacion(serie, settings)
    nominal_s = settings.sampling["nominal_sample_interval_s"]
    cobertura = phase_coverage(serie, fase.start_index, fase.end_index, nominal_s)
    assert cobertura.pct == 100.0
    assert cobertura.largest_blind_s == 0.0


def test_hueco_corto_no_dispara_las_reglas_de_cobertura(settings):
    """Un hueco de pocos segundos (ruido normal) no debe marcar cobertura baja.

    Desde la Fase 2, la cobertura ya no decide ningun veredicto (D6): esto
    prueba que el numero en si sigue siendo correcto, no que exista una regla
    que lo compare contra un umbral -esa regla ya no esta-.
    """
    serie = build_series_con_hueco(
        ciclo_plano(), desde_min=30.0, duracion_min=0.25, modo="celdas_vacias",
    )
    ciclo = segment(serie, settings)[0]
    assign(serie, ciclo, settings, P117)
    assert ciclo.coverage_pct > 99.0
    codigos = {f.code.value for f in ciclo.findings}
    assert "low_phase_coverage" not in codigos
    assert "blind_window_in_phase" not in codigos
