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


def reales(lista):
    """Sin la fila centinela del programa 0 ("Manual"), que `ensure_tables`
    crea siempre para que la clave ajena acepte los ciclos de consigna
    manual (ver `logic/schema.py`). No es un programa del autoclave, así que
    no cuenta en lo que estas pruebas miden."""
    return [p for p in lista if p.code != programs.MANUAL_PROGRAM_CODE]


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
    lista = reales(programs.list_programs(conn))
    assert len(lista) == 1
    assert lista[0].name == "P117"

    # Mismo codigo: actualiza en vez de duplicar.
    programs.upsert_program(
        conn, SterilizationProgram(code=1, name="P117 revisado", target_temperature_c=118.0, target_time_min=75.0)
    )
    lista = reales(programs.list_programs(conn))
    assert len(lista) == 1
    assert lista[0].name == "P117 revisado"
    assert lista[0].target_temperature_c == 118.0


def test_set_program_active_no_borra(conn):
    programs.upsert_program(
        conn, SterilizationProgram(code=2, name="P93", target_temperature_c=93.0, target_time_min=30.0)
    )
    programs.set_program_active(conn, 2, False)

    todos = reales(programs.list_programs(conn, include_inactive=True))
    assert len(todos) == 1
    assert todos[0].is_active is False

    activos = reales(programs.list_programs(conn, include_inactive=False))
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


def test_ensure_tables_crea_el_programa_manual_y_no_lo_duplica(conn):
    """La fila 0 tiene que existir porque `ferlo_cycle.program_code` es clave
    ajena contra esta tabla: sin ella no se podría guardar un ciclo con
    consigna manual."""
    manual = [p for p in programs.list_programs(conn) if p.code == programs.MANUAL_PROGRAM_CODE]
    assert len(manual) == 1
    assert manual[0].is_active is False

    ensure_tables(conn)  # idempotente (D8)
    manual = [p for p in programs.list_programs(conn) if p.code == programs.MANUAL_PROGRAM_CODE]
    assert len(manual) == 1


def test_manual_program_no_se_sugiere_nunca():
    """Teclear una consigna es una elección explícita, no algo que sugerir."""
    manual = programs.manual_program(117.0, 73.0)
    assert manual.is_active is False
    assert programs.suggest_programs([manual], 117.0) == []


def test_dos_consignas_manuales_no_se_pisan(conn):
    """El riesgo real del código 0 compartido: si la consigna se releyera de
    la fila 0, teclear una nueva cambiaría la de todos los ciclos manuales ya
    guardados. `manual_program` la construye al vuelo, así que no."""
    primera = programs.manual_program(118.5, 55.0)
    segunda = programs.manual_program(102.0, 12.0)

    assert (primera.target_temperature_c, primera.target_time_min) == (118.5, 55.0)
    assert (segunda.target_temperature_c, segunda.target_time_min) == (102.0, 12.0)

    fila = conn.execute(
        "SELECT target_temperature_c, target_time_min FROM ferlo_program WHERE code = 0"
    ).fetchone()
    assert (fila["target_temperature_c"], fila["target_time_min"]) == (0.0, 0.0)
