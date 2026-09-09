"""Etapa 3c - Criterios de aceptacion y marcado de revision.

    CORRECTO   media      >= consigna - acceptance_tolerance_c
           Y   duracion   >= tiempo    - acceptance_time_tolerance_min
           Y   media      <= consigna + max_over_temperature_c
           Y   duracion   <= tiempo    + max_extra_time_min

    A REVISAR  cumple lo anterior pero hay alguna incidencia de severidad REVIEW

La tolerancia de aceptacion es una variable distinta de la de deteccion de fase:
una encuentra la fase, la otra la juzga. Con el criterio estricto `media >=
consigna`, 12 de los 33 ciclos reales se rechazarian por 0,06-0,11 °C, que es
dispersion de calibracion entre maquinas (0,4 °C entre Ferlo3 y Ferlo4), no
fallo de proceso.

La regla de desviacion excluye la ventana de estabilizacion a proposito: el
sobreimpulso a 120-121,5 °C es sistematico en los 33 ciclos y, sin excluirlo, se
marcarian todos y el marcado dejaria de significar nada.
"""

from __future__ import annotations

from ..core.config import Settings
from ..core.enums import CycleStatus, FindingCode, Phase, Severity
from ..core.models import CycleResult, Finding, Series
from .phases import Dip


def validate(
    serie: Series,
    cycle: CycleResult,
    settings: Settings,
    dips: list[Dip],
) -> None:
    """Genera las incidencias del ciclo y fija su estado, in situ."""
    _heredar_incidencias(serie, cycle)
    _marcar_bajadas(cycle, dips, settings)
    _marcar_desviaciones(serie, cycle, settings)
    _marcar_cobertura(cycle, settings)

    fase = cycle.phases.get(Phase.STERILIZATION)
    if fase is None:
        cycle.findings.append(Finding(
            FindingCode.NO_PLATEAU, Severity.ERROR,
            "No se alcanza la banda de esterilizacion en todo el ciclo",
            ts=cycle.start_ts,
        ))
        cycle.status = CycleStatus.NON_CONFORMING
        return

    if cycle.program_code is None:
        cycle.status = CycleStatus.UNASSIGNED
        return

    if cycle.status is CycleStatus.INCOMPLETE:
        cycle.findings.append(Finding(
            FindingCode.INCOMPLETE_CYCLE, Severity.ERROR,
            "El fichero termina antes de completar el enfriamiento",
            ts=cycle.end_ts,
        ))
        return

    cycle.criteria = settings.criteria_snapshot()
    _aplicar_criterios(cycle, settings)

    if cycle.has(Severity.ERROR):
        cycle.status = CycleStatus.NON_CONFORMING
    elif cycle.has(Severity.REVIEW):
        cycle.status = CycleStatus.REVIEW
    else:
        cycle.status = CycleStatus.OK


def _aplicar_criterios(cycle: CycleResult, settings: Settings) -> None:
    acc = settings.acceptance
    tol_c = float(acc["acceptance_tolerance_c"])
    tol_min = float(acc["acceptance_time_tolerance_min"])
    max_over_c = float(acc["max_over_temperature_c"])
    max_extra_min = float(acc["max_extra_time_min"])

    consigna = cycle.target_temperature_c
    objetivo = cycle.target_time_min
    media = cycle.mean_temperature_c
    duracion = cycle.sterilization_duration_min
    if consigna is None or objetivo is None or media is None or duracion is None:
        return

    if media < consigna - tol_c:
        cycle.findings.append(Finding(
            FindingCode.UNDER_TEMPERATURE, Severity.ERROR,
            f"Media {media:.2f} °C < minimo admisible {consigna - tol_c:.2f} °C",
            ts=cycle.start_ts, value=media,
        ))
    elif media > consigna + max_over_c:
        cycle.findings.append(Finding(
            FindingCode.OVER_TEMPERATURE, Severity.ERROR,
            f"Media {media:.2f} °C > maximo admisible {consigna + max_over_c:.2f} °C",
            ts=cycle.start_ts, value=media,
        ))

    if duracion < objetivo - tol_min:
        cycle.findings.append(Finding(
            FindingCode.UNDER_TIME, Severity.ERROR,
            f"Duracion {duracion:.1f} min < minimo admisible {objetivo - tol_min:.1f} min",
            ts=cycle.start_ts, value=duracion,
        ))
    elif duracion > objetivo + max_extra_min:
        cycle.findings.append(Finding(
            FindingCode.OVER_TIME, Severity.ERROR,
            f"Duracion {duracion:.1f} min > maximo admisible {objetivo + max_extra_min:.1f} min",
            ts=cycle.start_ts, value=duracion,
        ))


def _heredar_incidencias(serie: Series, cycle: CycleResult) -> None:
    """Copia al ciclo las incidencias de la serie que caen dentro de su ventana.

    Es lo que hace que las anomalias de Ferlo5 de las 22:59 -50 minutos sin
    temperatura y una lectura de 3,4 °C- no invaliden ningun ciclo: ocurren
    despues del ultimo, que termina a las 22:03.
    """
    for f in serie.findings:
        if f.ts is not None and cycle.start_ts <= f.ts <= cycle.end_ts:
            if f.code is FindingCode.DATA_GAP:
                f = Finding(FindingCode.DATA_GAP_IN_PHASE, f.severity,
                            f.message, f.ts, f.value)
            cycle.findings.append(f)


def _marcar_bajadas(cycle: CycleResult, dips: list[Dip], settings: Settings) -> None:
    debounce = float(settings.sterilization_phase["exit_debounce_s"])
    for d in dips:
        cycle.findings.append(Finding(
            FindingCode.DIP_BELOW_BAND, Severity.REVIEW,
            f"Bajada bajo la banda de {d.duration_s:.0f} s "
            f"(minimo {d.min_temperature_c:.1f} °C), absorbida por el antirrebote "
            f"de {debounce:.0f} s",
            ts=d.start_ts, value=d.min_temperature_c,
        ))


def _marcar_cobertura(cycle: CycleResult, settings: Settings) -> None:
    """Compara la cobertura de datos de la esterilizacion (ya calculada por
    `compute_metrics`) contra los umbrales de `settings.coverage`.

    Trata igual una sonda con celdas vacias que un hueco de filas ausentes -son
    el mismo fallo fisico- porque `coverage_pct`/`max_blind_window_s` ya vienen
    de `phase_coverage`, que no distingue entre ambos casos.
    """
    cfg = settings.coverage
    if cycle.coverage_pct is not None:
        minimo = float(cfg["min_phase_coverage_pct"])
        if cycle.coverage_pct < minimo:
            cycle.findings.append(Finding(
                FindingCode.LOW_PHASE_COVERAGE, Severity.REVIEW,
                f"Cobertura de datos {cycle.coverage_pct:.1f} % < minimo admisible "
                f"{minimo:.0f} % ({cycle.uncovered_min:.1f} min sin lectura de fiar)",
                ts=cycle.start_ts, value=cycle.coverage_pct,
            ))
    if cycle.max_blind_window_s is not None:
        maximo = float(cfg["max_blind_window_s"])
        if cycle.max_blind_window_s > maximo:
            cycle.findings.append(Finding(
                FindingCode.BLIND_WINDOW_IN_PHASE, Severity.ERROR,
                f"Tramo sin datos de {cycle.max_blind_window_s:.0f} s dentro de la "
                f"esterilizacion (maximo admisible {maximo:.0f} s)",
                ts=cycle.start_ts, value=cycle.max_blind_window_s,
            ))


def _marcar_desviaciones(serie: Series, cycle: CycleResult, settings: Settings) -> None:
    fase = cycle.phases.get(Phase.STERILIZATION)
    consigna = cycle.evaluation_setpoint_c
    if fase is None or not consigna:
        return

    limite = float(settings.review["review_deviation_c"])
    ventana_s = float(settings.sterilization_phase["stabilization_window_min"]) * 60.0
    ts, temps = serie.ts, serie.temperature_c
    a = fase.start_index

    peor_ts = None
    peor = 0.0
    for i in range(a, fase.end_index + 1):
        v = temps[i]
        if v is None or (ts[i] - ts[a]).total_seconds() < ventana_s:
            continue
        desv = v - consigna
        if abs(desv) > limite and abs(desv) > abs(peor):
            peor, peor_ts = desv, ts[i]

    if peor_ts is not None:
        cycle.findings.append(Finding(
            FindingCode.DEVIATION_AFTER_STABILIZATION, Severity.REVIEW,
            f"Desviacion de {peor:+.1f} °C sobre la consigna fuera de la ventana "
            f"de estabilizacion",
            ts=peor_ts, value=peor,
        ))
