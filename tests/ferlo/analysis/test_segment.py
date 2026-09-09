from __future__ import annotations

from conftest import build_series, ciclo_tipico, meseta, rampa

from src.modules.ferlo.logic.analysis.models import CycleStatus
from src.modules.ferlo.logic.analysis.segment import estimate_setpoint, segment


def test_consigna_es_la_moda_no_el_pico(settings):
    """El sobreimpulso de la rampa no debe confundirse con la meseta.

    Es el error que fallaba en 4 de los 5 autoclaves reales: Ferlo1 sube a
    121,3 °C durante 4 min y luego se estabiliza en 117,1.
    """
    serie = build_series(ciclo_tipico(consigna=117.0, sobreimpulso=121.3))
    ciclos = segment(serie, settings)

    assert len(ciclos) == 1
    assert ciclos[0].measured_setpoint_c == 117.0
    assert ciclos[0].peak_temperature_c > 121.0  # el pico existe, pero no manda


def test_estimate_setpoint_ignora_rampa_y_enfriamiento():
    curva = rampa(30.0, 110.0, 200) + meseta(110.0, 60.0) + rampa(110.0, 30.0, 200)
    assert estimate_setpoint(curva, paso=0.1, suelo=60.0) == 110.0


def test_dos_ciclos_seguidos(settings):
    serie = build_series(ciclo_tipico() + ciclo_tipico())
    assert len(segment(serie, settings)) == 2


def test_descarta_repunte_corto(settings):
    """Una subida breve por encima de 50 °C no es un ciclo."""
    serie = build_series(rampa(40.0, 70.0, 30) + rampa(70.0, 40.0, 30) + ciclo_tipico())
    ciclos = segment(serie, settings)
    assert len(ciclos) == 1


def test_ciclo_cortado_al_final_del_fichero(settings):
    """Si el fichero acaba en plena meseta, el ciclo queda INCOMPLETE."""
    serie = build_series(rampa(40.0, 117.0, 120) + meseta(117.0, 40.0))
    ciclos = segment(serie, settings)
    assert len(ciclos) == 1
    assert ciclos[0].status is CycleStatus.INCOMPLETE


def test_huecos_de_temperatura_no_rompen_la_segmentacion(settings):
    curva: list[float | None] = list(ciclo_tipico())
    for i in range(500, 560):
        curva[i] = None
    serie = build_series(curva)
    assert len(segment(serie, settings)) == 1
