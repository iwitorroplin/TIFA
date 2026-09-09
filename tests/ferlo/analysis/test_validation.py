"""Portado (Fase 2) desde `legacy/sterilization_analysis/tests/test_validation.py`,
adaptado a la validacion reducida de D6 (ver `logic/analysis/validate.py`):

  * `test_tiempo_de_mas_excesivo_es_no_conformidad` desaparece: el criterio
    `over_time` que probaba ya no existe a proposito.
  * `test_el_sobreimpulso_puede_enmascarar_una_meseta_baja` gana una
    asercion de `status`: con las dos medias exigidas, este es justo el caso
    que D6 vino a corregir (antes pasaba solo con la media oficial).
  * `test_ciclo_muy_largo_ya_no_es_no_conformidad` es nuevo: fija el cambio
    de comportamiento en vez de dejarlo implicito.

El resto es identico al origen.
"""

from __future__ import annotations

from conftest import build_series, ciclo_plano, ciclo_tipico, meseta, rampa

from src.modules.ferlo.logic.analysis.models import CycleStatus, FindingCode, SterilizationProgram
from src.modules.ferlo.logic.analysis.service import analyze_series

P117 = SterilizationProgram(code=1, target_temperature_c=117.0, target_time_min=73.0)


def _codigos(ciclo):
    return {f.code for f in ciclo.findings}


def test_ciclo_conforme(settings):
    ciclos = analyze_series(build_series(ciclo_tipico()), settings, P117)
    assert len(ciclos) == 1
    assert ciclos[0].status is CycleStatus.OK


def test_sin_programa_queda_sin_veredicto(settings):
    ciclo = analyze_series(build_series(ciclo_tipico()), settings)[0]
    assert ciclo.status is CycleStatus.UNASSIGNED
    assert ciclo.target_temperature_c is None
    # aun asi las metricas se calculan, con la consigna medida
    assert ciclo.mean_temperature_c is not None
    assert ciclo.evaluation_setpoint_c == 117.0


def test_tolerancia_de_aceptacion_salva_el_desfase_de_calibracion(settings):
    """Caso Ferlo4/Ferlo5: media 0,06-0,11 °C por debajo de la consigna.

    Con criterio estricto se rechazarian 12 de los 33 ciclos reales.
    """
    ciclo = analyze_series(
        build_series(ciclo_plano(consigna=116.9)), settings, P117)[0]
    assert ciclo.status is CycleStatus.OK

    settings.acceptance["acceptance_tolerance_c"] = 0.0
    ciclo = analyze_series(
        build_series(ciclo_plano(consigna=116.9)), settings, P117)[0]
    assert ciclo.status is CycleStatus.NON_CONFORMING
    assert FindingCode.UNDER_TEMPERATURE in _codigos(ciclo)


def test_el_sobreimpulso_puede_enmascarar_una_meseta_baja(settings):
    """Consecuencia de que la media oficial incluya el sobreimpulso.

    Una meseta entera por debajo de la consigna puede dar media por encima si
    el sobreimpulso es grande. `mean_stable_temperature_c` si lo delata, y por
    eso se calcula aunque no sea la unica cifra oficial -y desde D6, tambien
    decide: exigir las dos medias es lo que hace que este ciclo ya no cuele-.
    """
    settings.acceptance["acceptance_tolerance_c"] = 0.0
    ciclo = analyze_series(
        build_series(ciclo_tipico(consigna=116.9, sobreimpulso=121.3)),
        settings, P117)[0]

    assert ciclo.mean_temperature_c > 117.0        # la media oficial no lo ve
    assert ciclo.mean_stable_temperature_c < 117.0  # la estable si
    assert ciclo.temperature_min_c < 117.0

    assert ciclo.status is CycleStatus.NON_CONFORMING
    assert FindingCode.UNDER_TEMPERATURE in _codigos(ciclo)


def test_tiempo_corto_es_no_conformidad(settings):
    ciclo = analyze_series(
        build_series(ciclo_plano(minutos_meseta=60.0)), settings, P117)[0]
    assert ciclo.status is CycleStatus.NON_CONFORMING
    assert FindingCode.UNDER_TIME in _codigos(ciclo)
    assert ciclo.time_deviation_min < 0
    assert ciclo.extra_time_min == 0.0  # no hay fase extra cuando falta tiempo


def test_tiempo_de_mas_dentro_de_tolerancia(settings):
    ciclo = analyze_series(
        build_series(ciclo_plano(minutos_meseta=75.0)), settings, P117)[0]
    assert ciclo.extra_time_min > 0
    assert ciclo.status is CycleStatus.OK


def test_ciclo_muy_largo_ya_no_es_no_conformidad(settings):
    """D6: sin techo de tiempo. Un ciclo mucho mas largo de lo pactado ya no
    se rechaza por eso -antes disparaba `over_time`-."""
    ciclo = analyze_series(
        build_series(ciclo_plano(minutos_meseta=90.0)), settings, P117)[0]
    assert ciclo.extra_time_min > 0
    assert ciclo.status is CycleStatus.OK
    assert "over_time" not in {c.value for c in _codigos(ciclo)}


def test_la_fase_dura_mas_que_la_meseta_por_el_sobreimpulso(settings):
    """La fase empieza al cruzar la banda, durante la rampa: el sobreimpulso
    cuenta como tiempo de esterilizacion. En Ferlo1 son ~3 min sobre los 70,3
    de meseta, que es como se llega a los 73,4 de fase."""
    con = analyze_series(
        build_series(ciclo_tipico(minutos_meseta=70.0)), settings, P117)[0]
    sin = analyze_series(
        build_series(ciclo_plano(minutos_meseta=70.0)), settings, P117)[0]
    assert con.sterilization_duration_min > sin.sterilization_duration_min + 3.0


def test_bajada_breve_marca_revision_sin_invalidar(settings):
    curva = (
        rampa(40.0, 117.0, 120) + meseta(117.0, 1.0) + [115.8] * 9
        + meseta(117.0, 72.0) + rampa(117.0, 40.0, 150)
    )
    ciclo = analyze_series(build_series(curva), settings, P117)[0]
    assert ciclo.status is CycleStatus.REVIEW
    assert FindingCode.DIP_BELOW_BAND in _codigos(ciclo)


def test_el_sobreimpulso_no_marca_revision(settings):
    """Es sistematico en los 33 ciclos reales: si marcase, marcaria todos y el
    marcado dejaria de significar nada."""
    ciclo = analyze_series(
        build_series(ciclo_tipico(sobreimpulso=121.5)), settings, P117)[0]
    assert FindingCode.DEVIATION_AFTER_STABILIZATION not in _codigos(ciclo)
    assert ciclo.status is CycleStatus.OK


def test_desviacion_tras_la_estabilizacion_si_marca(settings):
    curva = (
        rampa(40.0, 117.0, 120) + meseta(117.0, 30.0)
        + meseta(119.0, 5.0)          # +2 °C bien pasada la ventana
        + meseta(117.0, 38.0) + rampa(117.0, 40.0, 150)
    )
    ciclo = analyze_series(build_series(curva), settings, P117)[0]
    assert FindingCode.DEVIATION_AFTER_STABILIZATION in _codigos(ciclo)
    assert ciclo.status is CycleStatus.REVIEW


def test_los_criterios_quedan_congelados_en_el_ciclo(settings):
    """Sin esto, subir manana una tolerancia cambiaria veredictos ya emitidos."""
    ciclo = analyze_series(build_series(ciclo_tipico()), settings, P117)[0]
    assert ciclo.criteria["acceptance_tolerance_c"] == 0.5
    assert ciclo.criteria["exit_debounce_s"] == 60
