"""Fase 4: consultas de ciclos (`logic/analysis/repo.py`) que alimentan la
pestaña de Ciclos y el diálogo de detalle.

Conexión en memoria y llamadas directas a `repo.*` -sin pasar por
`logic/analysis/queries.py`, que abre su propia conexión a `tifa.db` y por
tanto no es lo que hay que probar aquí (ver `test_schema.py`)-.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import pytest

from src.modules.ferlo.logic.analysis import repo
from src.modules.ferlo.logic.analysis.models import (
    CycleStatus,
    ManualVerdict,
    Series,
    SterilizationProgram,
)
from src.modules.ferlo.logic.analysis.service import analyze_series
from src.modules.ferlo.logic.config import default_settings
from src.modules.ferlo.logic.schema import ensure_tables

P117 = SterilizationProgram(code=1, name="P117", target_temperature_c=117.0, target_time_min=73.0)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    ensure_tables(c)
    c.execute(
        "INSERT INTO ferlo_program (code, name, target_temperature_c, target_time_min)"
        " VALUES (1, 'P117', 117.0, 73.0)"
    )
    try:
        yield c
    finally:
        c.close()


def _serie_con_ciclo(machine: str, inicio: dt.datetime) -> Series:
    """Un ciclo simple y completo: rampa, meseta de 73 min a 117 °C, bajada."""
    serie = Series(autoclave_id=0, autoclave_name=machine, source_filename="test.csv")
    valores = (
        [40.0 + i * 3.85 for i in range(20)]
        + [117.0] * 876
        + [40.0 + (20 - i) * 3.85 for i in range(20)]
    )
    for i, v in enumerate(valores):
        serie.ts.append(inicio + dt.timedelta(seconds=i * 5))
        serie.temperature_c.append(v)
        serie.pressure_bar.append(0.0)
    return serie


def _guardar_ciclo(conn, machine: str, inicio: dt.datetime, program=P117):
    settings = default_settings()
    serie = _serie_con_ciclo(machine, inicio)
    ciclo = analyze_series(serie, settings, program)[0]
    cycle_id = repo.save_cycle(conn, machine, serie, ciclo)
    return cycle_id, ciclo


def test_list_cycles_filtra_por_maquina(conn):
    id_f2, _ = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0))
    id_f3, _ = _guardar_ciclo(conn, "F3", dt.datetime(2026, 8, 1, 6, 0, 0))

    filas = repo.list_cycles(conn, machine="F2", limit=50)
    assert {f.id for f in filas} == {id_f2}
    assert repo.count_cycles(conn, machine="F3") == 1
    assert repo.count_cycles(conn) == 2


def test_list_cycles_filtra_por_rango_de_fechas(conn):
    _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0))
    id_agosto_tarde, _ = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 20, 6, 0, 0))
    _guardar_ciclo(conn, "F2", dt.datetime(2026, 9, 5, 6, 0, 0))

    filas = repo.list_cycles(
        conn, date_from=dt.date(2026, 8, 15), date_to=dt.date(2026, 8, 31), limit=50
    )
    assert {f.id for f in filas} == {id_agosto_tarde}


def test_list_cycles_ordena_del_mas_reciente(conn):
    id_1, _ = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0))
    id_3, _ = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 3, 6, 0, 0))

    filas = repo.list_cycles(conn, limit=50)
    assert [f.id for f in filas] == [id_3, id_1]
    assert filas[0].started_at > filas[1].started_at


def test_needs_review_marca_lo_no_ok_y_sin_veredicto_manual(conn):
    # Ciclo conforme: no necesita revision.
    id_ok, ciclo_ok = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0))
    assert ciclo_ok.status is CycleStatus.OK

    # Ciclo sin programa asignado: UNASSIGNED, necesita revision.
    id_sin_programa, ciclo_sin = _guardar_ciclo(
        conn, "F2", dt.datetime(2026, 8, 2, 6, 0, 0), program=None
    )
    assert ciclo_sin.status is CycleStatus.UNASSIGNED

    filas = {f.id: f for f in repo.list_cycles(conn, needs_review=True, limit=50)}
    assert set(filas) == {id_sin_programa}
    assert repo.count_cycles(conn, needs_review=True) == 1

    # Una vez que alguien lo revisa a mano, deja de contar como pendiente
    # aunque el estado calculado no cambie.
    repo.set_manual_verdict(conn, id_sin_programa, ManualVerdict.CONFORMING, "visto bien")
    assert repo.count_cycles(conn, needs_review=True) == 0


def test_get_cycle_trae_el_nombre_del_programa(conn):
    cycle_id, _ = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0))
    fila = repo.get_cycle(conn, cycle_id)
    assert fila is not None
    assert fila.program_code == 1
    assert fila.program_name == "P117"


def test_get_cycle_sin_programa_no_revienta_el_join(conn):
    cycle_id, _ = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0), program=None)
    fila = repo.get_cycle(conn, cycle_id)
    assert fila.program_code is None
    assert fila.program_name == ""


def test_list_samples_y_list_incidents(conn):
    cycle_id, ciclo = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0))

    muestras = repo.list_samples(conn, cycle_id)
    assert len(muestras) == ciclo.end_index - ciclo.start_index + 1
    # En orden de tiempo, no el orden en que se insertaron.
    assert muestras == sorted(muestras, key=lambda par: par[0])

    incidencias = repo.list_incidents(conn, cycle_id)
    assert isinstance(incidencias, list)


def test_set_manual_verdict_no_toca_el_status_calculado(conn):
    cycle_id, ciclo = _guardar_ciclo(conn, "F2", dt.datetime(2026, 8, 1, 6, 0, 0))
    repo.set_manual_verdict(conn, cycle_id, ManualVerdict.NON_CONFORMING, "fuga en la puerta")

    fila = repo.get_cycle(conn, cycle_id)
    assert fila.manual_verdict == "non_conforming"
    assert fila.review_notes == "fuga en la puerta"
    assert fila.status is ciclo.status  # el veredicto automatico no se pisa
