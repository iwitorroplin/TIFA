from __future__ import annotations

from conftest import build_series, ciclo_tipico, meseta, rampa

from src.modules.ferlo.logic.analysis.models import Phase
from src.modules.ferlo.logic.analysis.phases import detect_phases
from src.modules.ferlo.logic.analysis.segment import segment


def _fase(serie, settings, consigna=117.0):
    ciclos = segment(serie, settings)
    assert len(ciclos) == 1
    fases, dips = detect_phases(serie, ciclos[0], consigna, settings)
    return fases, dips


def test_bajada_breve_no_corta_la_fase(settings):
    """Caso Ferlo5: oscila y baja de la banda a los 65 s de entrar.

    Con la regla literal 'termina al bajar de la banda' el ciclo duraria 65
    segundos en vez de 75 minutos.
    """
    curva = (
        rampa(40.0, 117.0, 120)
        + meseta(117.0, 1.0)
        + [115.8] * 9          # 45 s bajo la banda, por debajo del antirrebote
        + meseta(117.0, 70.0)
        + rampa(117.0, 40.0, 150)
    )
    fases, dips = _fase(build_series(curva), settings)

    ester = fases[Phase.STERILIZATION]
    assert ester.duration_min > 70.0
    assert len(dips) == 1
    assert dips[0].duration_s == 45.0
    assert dips[0].min_temperature_c == 115.8


def test_bajada_larga_si_corta_la_fase(settings):
    curva = (
        rampa(40.0, 117.0, 120)
        + meseta(117.0, 20.0)
        + [110.0] * 30         # 150 s: supera el antirrebote de 60 s
        + meseta(117.0, 20.0)
        + rampa(117.0, 40.0, 150)
    )
    fases, _ = _fase(build_series(curva), settings)
    assert 19.5 < fases[Phase.STERILIZATION].duration_min < 21.0


def test_el_enfriamiento_final_no_se_reporta_como_bajada(settings):
    """Regresion: el enfriamiento superaba el antirrebote y aun asi se
    registraba como bajada, marcando los 33 ciclos reales para revision."""
    fases, dips = _fase(build_series(ciclo_tipico()), settings)
    assert dips == []
    assert Phase.COOLING in fases


def test_las_tres_fases_encadenan(settings):
    fases, _ = _fase(build_series(ciclo_tipico()), settings)
    calent, ester, enfr = (
        fases[Phase.HEATING], fases[Phase.STERILIZATION], fases[Phase.COOLING]
    )
    assert calent.end_ts == ester.start_ts
    assert ester.end_ts == enfr.start_ts
    assert calent.duration_min > 0 and enfr.duration_min > 0


def test_sin_meseta_no_hay_fase(settings):
    """Un ciclo que nunca alcanza la banda no produce fase de esterilizacion."""
    curva = rampa(40.0, 90.0, 200) + meseta(90.0, 30.0) + rampa(90.0, 40.0, 200)
    serie = build_series(curva)
    ciclos = segment(serie, settings)
    fases, _ = detect_phases(serie, ciclos[0], 117.0, settings)
    assert fases == {}
