"""Etapa 3c - Criterios de aceptacion y marcado de revision.

Reducido en la Fase 2 del port (decision D6, "las dos, y que cumplan las
dos"): la version original tenia cuatro criterios (bajo/sobre temperatura,
bajo/sobre tiempo). Aqui quedan dos, y sin techo:

    CORRECTO   media oficial   >= consigna - acceptance_tolerance_c
           Y   media estable   >= consigna - acceptance_tolerance_c
           Y   duracion        >= tiempo de consigna - acceptance_time_tolerance_min

    A REVISAR  cumple lo anterior pero hay alguna incidencia de severidad REVIEW

Exigir las dos medias es justo lo que el criterio antiguo (solo la oficial)
no hacia: un sobreimpulso grande puede dejar la media oficial por encima de
consigna con la meseta entera por debajo (ver
`legacy/sterilization_analysis/.../metrics.py`, docstring de
`mean_stable_temperature_c`). `over_temperature`/`over_time` desaparecen: un
ciclo mas caliente o mas largo de lo pactado ya no se rechaza por eso -el
codigo que los emitia sigue en `legacy/sterilization_analysis/` mientras ese
repo exista-. La cobertura y el tiempo bajo consigna se calculan en
metrics.py y se muestran, pero no deciden aqui.

La tolerancia de aceptacion es una variable distinta de la de deteccion de
fase: una encuentra la fase, la otra la juzga. La regla de desviacion excluye
la ventana de estabilizacion a proposito: el sobreimpulso es sistematico y,
sin excluirlo, se marcarian todos los ciclos y el marcado dejaria de
significar nada.
"""

from __future__ import annotations

from ..config import Settings
from .models import CycleResult, CycleStatus, Finding, FindingCode, Phase, Series, Severity
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

    consigna = cycle.target_temperature_c
    objetivo = cycle.target_time_min
    media = cycle.mean_temperature_c
    media_estable = cycle.mean_stable_temperature_c
    duracion = cycle.sterilization_duration_min
    if (
        consigna is None or objetivo is None
        or media is None or media_estable is None or duracion is None
    ):
        return

    minimo_c = consigna - tol_c
    if media < minimo_c:
        cycle.findings.append(Finding(
            FindingCode.UNDER_TEMPERATURE, Severity.ERROR,
            f"Media oficial {media:.2f} °C < minimo admisible {minimo_c:.2f} °C",
            ts=cycle.start_ts, value=media,
        ))
    if media_estable < minimo_c:
        cycle.findings.append(Finding(
            FindingCode.UNDER_TEMPERATURE, Severity.ERROR,
            f"Media estable {media_estable:.2f} °C < minimo admisible {minimo_c:.2f} °C",
            ts=cycle.start_ts, value=media_estable,
        ))

    minimo_min = objetivo - tol_min
    if duracion < minimo_min:
        cycle.findings.append(Finding(
            FindingCode.UNDER_TIME, Severity.ERROR,
            f"Duracion {duracion:.1f} min < minimo admisible {minimo_min:.1f} min",
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
