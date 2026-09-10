"""`_resolve_program`: qué consigna se aplica al reasignar un ciclo.

Es el punto donde se decide entre "el programa que dice la lista" y "la
consigna que tecleó una persona" (ver `logic/ingest/service.py`).
"""

from __future__ import annotations

import sqlite3

import pytest

from src.modules.ferlo.logic.analysis import programs
from src.modules.ferlo.logic.analysis.models import SterilizationProgram
from src.modules.ferlo.logic.analysis.programs import ManualSetpoint
from src.modules.ferlo.logic.ingest.service import _resolve_program
from src.modules.ferlo.logic.schema import ensure_tables


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    ensure_tables(c)
    programs.upsert_program(
        c, SterilizationProgram(code=23, name="Piperrade", target_temperature_c=117.0, target_time_min=73.0)
    )
    try:
        yield c
    finally:
        c.close()


def test_sin_programa_ni_manual_no_asigna_nada(conn):
    assert _resolve_program(conn, None, None) is None


def test_codigo_carga_el_programa_de_la_tabla(conn):
    p = _resolve_program(conn, 23, None)
    assert (p.code, p.target_temperature_c, p.target_time_min) == (23, 117.0, 73.0)


def test_manual_no_lee_la_tabla(conn):
    p = _resolve_program(conn, programs.MANUAL_PROGRAM_CODE, ManualSetpoint(118.5, 55.0))
    assert p.code == programs.MANUAL_PROGRAM_CODE
    assert (p.target_temperature_c, p.target_time_min) == (118.5, 55.0)


def test_manual_gana_al_codigo(conn):
    """La pantalla manda el código 0 junto a la consigna manual; si alguna
    ruta mandara otro código, la consigna tecleada sigue siendo la que vale."""
    p = _resolve_program(conn, 23, ManualSetpoint(102.0, 12.0))
    assert (p.target_temperature_c, p.target_time_min) == (102.0, 12.0)
