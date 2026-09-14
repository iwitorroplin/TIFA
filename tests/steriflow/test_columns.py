"""Etiquetas de las celdas de la tabla de ciclos (`logic/sterilization/columns.py`)
que no son un campo tal cual del ciclo."""

from __future__ import annotations

import datetime as dt

from src.modules.steriflow.logic.sterilization.columns import autoclave_label, phase_label
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle


def _ciclo(**campos) -> SterilizationCycle:
    return SterilizationCycle(
        autoclave_code=8,
        started_at=dt.datetime(2026, 9, 9, 18, 24, 17),
        source_filename="MPI_10_011_-_TOMATE_PELADO__1KG.pdf",
        source_sha256="",
        **campos,
    )


def test_autoclave_con_nombre_configurado():
    assert autoclave_label(_ciclo(autoclave="AUTOCLAVE8")) == "AUTOCLAVE8"


def test_autoclave_sin_nombre_se_compone_con_el_numero():
    """Ciclos guardados antes de que se guardara el nombre de la máquina."""
    assert autoclave_label(_ciclo()) == "AUTOCLAVE8"


def test_fase_sin_leer():
    assert phase_label(_ciclo()) == "—"


def test_fase_sin_tipo():
    assert phase_label(_ciclo(sterilization_phase_number=3)) == "3"


def test_fase_con_tipo():
    ciclo = _ciclo(sterilization_phase_number=3, sterilization_phase_type="Esterilización")
    assert phase_label(ciclo) == "3 · Esterilización"
