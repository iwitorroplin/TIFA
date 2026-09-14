"""`_build_filters`, vía `list_cycles`/`count_cycles`, para el filtro de
autoclave del combo de selección múltiple (ver
`src/shared/ui/components/multi_select_combo_box.py` y `ui/data_page/
filters_row.py`): None es "todas, sin filtrar" y una secuencia vacía -combo
con todas las autoclaves desmarcadas- es un filtro real que no debe casar
con nada, no lo mismo que None.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import pytest

from src.modules.steriflow.logic.schema import ensure_tables
from src.modules.steriflow.logic.sterilization import repo
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ensure_tables(c)
    try:
        yield c
    finally:
        c.close()


def _ciclo(autoclave_code: int, inicio: dt.datetime) -> SterilizationCycle:
    return SterilizationCycle(
        autoclave_code=autoclave_code,
        autoclave=f"AUTOCLAVE{autoclave_code}",
        started_at=inicio,
        source_filename=f"MPI_{autoclave_code}_{inicio:%Y%m%d%H%M}.pdf",
        source_sha256=f"sha-{autoclave_code}-{inicio.isoformat()}",
    )


def test_autoclave_codes_none_no_filtra(conn):
    repo.save_cycle(conn, _ciclo(6, dt.datetime(2026, 8, 1, 6, 0, 0)))
    repo.save_cycle(conn, _ciclo(7, dt.datetime(2026, 8, 1, 6, 0, 0)))

    assert repo.count_cycles(conn, autoclave_codes=None) == 2
    assert len(repo.list_cycles(conn, autoclave_codes=None)) == 2


def test_autoclave_codes_filtra_por_los_indicados(conn):
    repo.save_cycle(conn, _ciclo(6, dt.datetime(2026, 8, 1, 6, 0, 0)))
    repo.save_cycle(conn, _ciclo(7, dt.datetime(2026, 8, 1, 6, 0, 0)))
    repo.save_cycle(conn, _ciclo(8, dt.datetime(2026, 8, 1, 6, 0, 0)))

    filas = repo.list_cycles(conn, autoclave_codes=[6, 8])
    assert {f.autoclave_code for f in filas} == {6, 8}
    assert repo.count_cycles(conn, autoclave_codes=[6, 8]) == 2


def test_autoclave_codes_vacio_no_devuelve_nada(conn):
    """Combo con todas las autoclaves desmarcadas: filtro real -"ninguna"-,
    distinto de `autoclave_codes=None` (sin filtrar)."""
    repo.save_cycle(conn, _ciclo(6, dt.datetime(2026, 8, 1, 6, 0, 0)))

    assert repo.list_cycles(conn, autoclave_codes=[]) == []
    assert repo.count_cycles(conn, autoclave_codes=[]) == 0
