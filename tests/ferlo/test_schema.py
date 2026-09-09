"""Fase 3: esquema de Ferlo en `tifa.db` y persistencia de un `CycleResult`.

Conexion en memoria, aislada de `data/tifa.db`: `ensure_tables` se llama
directo, sin pasar por el registro global de `src/shared/db/schema.py` (eso
lo hace `src/__main__.py`/`web/registry.py` al arrancar la app de verdad).
"""

from __future__ import annotations

import sqlite3
import datetime as dt

import pytest

from src.modules.ferlo.logic.analysis.models import Series, SterilizationProgram
from src.modules.ferlo.logic.analysis.repo import save_cycle
from src.modules.ferlo.logic.analysis.service import analyze_series
from src.modules.ferlo.logic.config import default_settings
from src.modules.ferlo.logic.schema import ensure_tables

P117 = SterilizationProgram(code=1, target_temperature_c=117.0, target_time_min=73.0)
INICIO = dt.datetime(2026, 8, 1, 6, 0, 0)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    ensure_tables(c)
    # ferlo_cycle.program_code es FK a ferlo_program: un ciclo solo puede
    # referenciar un programa que ya exista, igual que en produccion.
    c.execute(
        "INSERT INTO ferlo_program (code, name, target_temperature_c, target_time_min)"
        " VALUES (1, 'P117', 117.0, 73.0)"
    )
    try:
        yield c
    finally:
        c.close()


def _ciclo_tipico_serie() -> Series:
    """Un ciclo simple y completo: rampa, meseta de 73 min a 117 °C, bajada."""
    serie = Series(autoclave_id=1, autoclave_name="F2", source_filename="test.csv")
    t = INICIO
    valores = (
        [40.0 + i * 3.85 for i in range(20)]  # rampa: 40 -> ~117 en 100 min... (paso grueso, solo para el test)
        + [117.0] * 876   # 73 min a intervalo de 5 s
        + [40.0 + (20 - i) * 3.85 for i in range(20)]
    )
    for i, v in enumerate(valores):
        serie.ts.append(t + dt.timedelta(seconds=i * 5))
        serie.temperature_c.append(v)
        serie.pressure_bar.append(0.0)
    return serie


def test_ensure_tables_crea_las_tablas(conn):
    tablas = {
        r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ferlo_%'"
        ).fetchall()
    }
    assert tablas == {"ferlo_import", "ferlo_program", "ferlo_cycle", "ferlo_sample", "ferlo_incident"}


def test_ensure_tables_es_idempotente(conn):
    ensure_tables(conn)  # segunda vez, no debe fallar
    ensure_tables(conn)


def test_guardar_un_ciclo_y_sus_muestras(conn):
    serie = _ciclo_tipico_serie()
    settings = default_settings()
    ciclos = analyze_series(serie, settings, P117)
    assert len(ciclos) == 1
    ciclo = ciclos[0]

    cycle_id = save_cycle(conn, "F2", serie, ciclo)

    fila = conn.execute("SELECT * FROM ferlo_cycle WHERE id = ?", (cycle_id,)).fetchone()
    assert fila["machine"] == "F2"
    assert fila["status"] == ciclo.status.value
    assert fila["manual_verdict"] == "none"
    assert fila["program_code"] == 1

    n_muestras = conn.execute(
        "SELECT COUNT(*) AS n FROM ferlo_sample WHERE cycle_id = ?", (cycle_id,)
    ).fetchone()["n"]
    assert n_muestras == ciclo.end_index - ciclo.start_index + 1


def test_reguardar_no_duplica_y_conserva_lo_decidido_a_mano(conn):
    """Invariante de la Fase 0: reimportar nunca deshace una asignacion ni un
    veredicto manual."""
    serie = _ciclo_tipico_serie()
    settings = default_settings()
    ciclo = analyze_series(serie, settings, P117)[0]

    cycle_id = save_cycle(conn, "F2", serie, ciclo)
    conn.execute(
        "UPDATE ferlo_cycle SET manual_verdict='conforming', review_notes='visto bien' WHERE id=?",
        (cycle_id,),
    )

    # Reanaliza (p.ej. tras cambiar un umbral) y vuelve a guardar
    ciclo2 = analyze_series(serie, settings, P117)[0]
    otro_id = save_cycle(conn, "F2", serie, ciclo2)

    assert otro_id == cycle_id
    total = conn.execute("SELECT COUNT(*) AS n FROM ferlo_cycle").fetchone()["n"]
    assert total == 1

    fila = conn.execute("SELECT * FROM ferlo_cycle WHERE id = ?", (cycle_id,)).fetchone()
    assert fila["manual_verdict"] == "conforming"
    assert fila["review_notes"] == "visto bien"


def test_reguardar_reemplaza_muestras_e_incidencias(conn):
    serie = _ciclo_tipico_serie()
    settings = default_settings()
    ciclo = analyze_series(serie, settings, P117)[0]

    cycle_id = save_cycle(conn, "F2", serie, ciclo)
    n1 = conn.execute(
        "SELECT COUNT(*) AS n FROM ferlo_sample WHERE cycle_id=?", (cycle_id,)
    ).fetchone()["n"]

    save_cycle(conn, "F2", serie, ciclo)  # mismo ciclo, otra vez
    n2 = conn.execute(
        "SELECT COUNT(*) AS n FROM ferlo_sample WHERE cycle_id=?", (cycle_id,)
    ).fetchone()["n"]

    assert n1 == n2  # no se duplican
