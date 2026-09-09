"""Fase 0 del port de Ferlo: fija los numeros de la normalizacion actual.

`legacy/sterilization_data_ferlo/database/ferlo.db` es la base ya poblada por
el formatter del origen (F2, ene-2020 a ago-2026). No hay que fabricar una
referencia sintetica: ese fichero de 2,9 GB *es* la referencia. Si el lector
nuevo de la Fase 1 (`logic/ingest/`) alguna vez reproduce esta importacion,
tiene que dar exactamente estos numeros -si no coinciden, es que un umbral o
una regla de normalizacion cambio, no que el codigo "mejorase" en silencio.

Solo lee (`mode=ro`): son 2,9 GB compartidos con el resto de la maquina del
usuario y este test no tiene ningun motivo para escribir en ellos.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "legacy" / "sterilization_data_ferlo" / "database" / "ferlo.db"
)

# Congelados el 2026-09-09 contra el ferlo.db real (ver el documento de la
# Fase 0). Si cambian, es el umbral el que se movio.
TOTAL_FILAS = 18_008_315
TEMPERATURAS_NULAS = 46
PRESIONES_NULAS = 863_000
MAQUINAS_CARGADAS = {"F2"}


@pytest.fixture(scope="module")
def conn():
    if not DB_PATH.exists():
        pytest.skip(f"falta {DB_PATH} (no se ha vendorizado legacy/sterilization_data_ferlo)")
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        yield con
    finally:
        con.close()


def test_total_de_filas(conn):
    (total,) = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()
    assert total == TOTAL_FILAS


def test_temperaturas_no_interpretables(conn):
    (n,) = conn.execute(
        "SELECT COUNT(*) FROM measurements WHERE temperature IS NULL"
    ).fetchone()
    assert n == TEMPERATURAS_NULAS


def test_presiones_no_interpretables(conn):
    """El '<<<<<<<<' que escribe el equipo cuando la sonda de presion no
    da lectura: ~4,8 % de las filas, y ninguna se descarta por eso."""
    (n,) = conn.execute(
        "SELECT COUNT(*) FROM measurements WHERE pressure IS NULL"
    ).fetchone()
    assert n == PRESIONES_NULAS


def test_solo_las_maquinas_esperadas_estan_cargadas(conn):
    filas = conn.execute("SELECT DISTINCT machine FROM measurements").fetchall()
    assert {m for (m,) in filas} == MAQUINAS_CARGADAS
