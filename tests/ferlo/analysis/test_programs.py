"""Fase 4: gestión manual de `ferlo_program` (`logic/analysis/programs.py`).

Ver el docstring del módulo: no hay Excel de origen que portar, así que la
tabla se gestiona desde la pestaña de Configuración con estas mismas
funciones.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.modules.ferlo.logic.analysis import programs
from src.modules.ferlo.logic.analysis.models import SterilizationProgram
from src.modules.ferlo.logic.schema import ensure_tables


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    ensure_tables(c)
    try:
        yield c
    finally:
        c.close()


def test_upsert_program_crea_y_luego_actualiza(conn):
    programs.upsert_program(
        conn, SterilizationProgram(code=1, name="P117", target_temperature_c=117.0, target_time_min=73.0)
    )
    lista = programs.list_programs(conn)
    assert len(lista) == 1
    assert lista[0].name == "P117"

    # Mismo codigo: actualiza en vez de duplicar.
    programs.upsert_program(
        conn, SterilizationProgram(code=1, name="P117 revisado", target_temperature_c=118.0, target_time_min=75.0)
    )
    lista = programs.list_programs(conn)
    assert len(lista) == 1
    assert lista[0].name == "P117 revisado"
    assert lista[0].target_temperature_c == 118.0


def test_set_program_active_no_borra(conn):
    programs.upsert_program(
        conn, SterilizationProgram(code=2, name="P93", target_temperature_c=93.0, target_time_min=30.0)
    )
    programs.set_program_active(conn, 2, False)

    todos = programs.list_programs(conn, include_inactive=True)
    assert len(todos) == 1
    assert todos[0].is_active is False

    activos = programs.list_programs(conn, include_inactive=False)
    assert activos == []


def test_suggest_programs_reduce_a_los_cercanos_y_activos():
    catalogo = [
        SterilizationProgram(code=1, name="A", target_temperature_c=117.0, target_time_min=73.0),
        SterilizationProgram(code=2, name="B", target_temperature_c=117.5, target_time_min=60.0),
        SterilizationProgram(code=3, name="C (inactivo)", target_temperature_c=117.2, target_time_min=50.0, is_active=False),
        SterilizationProgram(code=4, name="D (lejos)", target_temperature_c=134.0, target_time_min=15.0),
    ]

    sugeridos = programs.suggest_programs(catalogo, measured_setpoint_c=117.0, tolerance_c=2.0)

    assert [p.code for p in sugeridos] == [1, 2]  # ordenados por cercania, sin el inactivo ni el lejano


def test_suggest_programs_vacio_si_ninguno_esta_cerca():
    catalogo = [
        SterilizationProgram(code=1, name="A", target_temperature_c=134.0, target_time_min=15.0),
    ]
    assert programs.suggest_programs(catalogo, measured_setpoint_c=117.0) == []
