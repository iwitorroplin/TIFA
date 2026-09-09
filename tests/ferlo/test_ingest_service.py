"""Fase 4: `logic/ingest/service.py:reassign_program`, la única escritura de
`program_code` que no viene de una reimportación (invariante de la Fase 0:
"importar nunca asigna programa; asignar es siempre un acto explícito").

Construye un mensual sintético directamente con `archive.append_rows` -así
la prueba no depende de ningún CSV real- y lo analiza sin pasar por
`import_machine` (que además tendría que gestionar la carpeta de entrada).
"""

from __future__ import annotations

import copy
import datetime as dt
import sqlite3

import pytest

from src.modules.ferlo.logic.analysis import repo as analysis_repo
from src.modules.ferlo.logic.analysis.models import CycleStatus, ManualVerdict
from src.modules.ferlo.logic.analysis.segment import segment
from src.modules.ferlo.logic.config import DEFAULT_SETTINGS, Settings
from src.modules.ferlo.logic.ingest import archive
from src.modules.ferlo.logic.ingest.normalize import build_series
from src.modules.ferlo.logic.ingest.reader import RawRow, read_raw_rows
from src.modules.ferlo.logic.ingest.service import reassign_program
from src.modules.ferlo.logic.schema import ensure_tables

MACHINE = "F2"
INICIO = dt.datetime(2026, 8, 1, 6, 0, 0)


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


@pytest.fixture
def settings(tmp_path):
    data = copy.deepcopy(DEFAULT_SETTINGS)
    data["paths"]["entrada"] = str(tmp_path / "entrada")
    data["paths"]["archivo"] = str(tmp_path / "archivo")
    return Settings(data)


def _fila(momento: dt.datetime, temperatura: float) -> RawRow:
    return RawRow(
        date_raw=momento.strftime("%d/%m/%Y"),
        time_raw=momento.strftime("%H:%M:%S").lstrip("0") or "0",
        temperature_raw=str(temperatura).replace(".", ","),
        pressure_raw="0,000",
    )


def _archivar_ciclo_tipico(settings: Settings) -> dt.datetime:
    """Rampa, meseta de 73 min a 117 °C, bajada -directo al mensual del
    archivo, como si ya hubiera sido importado en un pase anterior.

    Devuelve el `start_ts` real del ciclo segmentado: la rampa cruza 50 °C
    unas cuantas muestras después de `INICIO`, no exactamente en `INICIO`
    (igual que en datos reales, ver `logic/analysis/segment.py`)."""
    valores = (
        [40.0 + i * 3.85 for i in range(20)]
        + [117.0] * 876
        + [40.0 + (20 - i) * 3.85 for i in range(20)]
    )
    filas = [_fila(INICIO + dt.timedelta(seconds=i * 5), v) for i, v in enumerate(valores)]
    ruta = archive.append_rows(settings.archivo_dir, MACHINE, INICIO.year, INICIO.month, filas)

    rows = read_raw_rows(ruta)
    serie = build_series(MACHINE, ruta.name, rows)
    return segment(serie, settings)[0].start_ts


def test_reassign_program_asigna_y_evalua(conn, settings):
    start_ts = _archivar_ciclo_tipico(settings)

    ciclo = reassign_program(conn, settings, MACHINE, start_ts, program_code=1)

    assert ciclo is not None
    assert ciclo.program_code == 1
    assert ciclo.status is CycleStatus.OK

    fila = analysis_repo.get_cycle(conn, analysis_repo.list_cycles(conn, limit=1)[0].id)
    assert fila.program_code == 1
    assert fila.program_name == "P117"


def test_reassign_program_con_none_desasigna(conn, settings):
    start_ts = _archivar_ciclo_tipico(settings)
    reassign_program(conn, settings, MACHINE, start_ts, program_code=1)

    ciclo = reassign_program(conn, settings, MACHINE, start_ts, program_code=None)

    assert ciclo.program_code is None
    assert ciclo.status is CycleStatus.UNASSIGNED
    fila = analysis_repo.list_cycles(conn, limit=1)[0]
    assert fila.program_code is None


def test_reassign_program_no_pisa_el_veredicto_manual(conn, settings):
    """El manual_verdict/review_notes no vive en CycleResult -solo en la fila
    guardada- así que reasignar programa (que recalcula y regrarda con
    save_cycle) no puede perderlo (ver repo.save_cycle)."""
    start_ts = _archivar_ciclo_tipico(settings)
    reassign_program(conn, settings, MACHINE, start_ts, program_code=1)
    cycle_id = analysis_repo.list_cycles(conn, limit=1)[0].id
    analysis_repo.set_manual_verdict(conn, cycle_id, ManualVerdict.CONFORMING, "visto en planta")

    reassign_program(conn, settings, MACHINE, start_ts, program_code=1)

    fila = analysis_repo.get_cycle(conn, cycle_id)
    assert fila.manual_verdict == "conforming"
    assert fila.review_notes == "visto en planta"


def test_reassign_program_sin_mensual_devuelve_none(conn, settings):
    assert reassign_program(conn, settings, MACHINE, INICIO, program_code=1) is None


def test_reassign_program_ciclo_inexistente_devuelve_none(conn, settings):
    _archivar_ciclo_tipico(settings)
    otro_instante = INICIO + dt.timedelta(days=1)
    assert reassign_program(conn, settings, MACHINE, otro_instante, program_code=1) is None
