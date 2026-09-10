"""Qué autoclave se le pone a un ciclo recién extraído
(`logic/sterilization/service.py:_aplicar_autoclave`).

El número que imprime el informe no es de fiar como identidad: la AUTOCLAVE8
imprime 10 en todos los suyos (sus PDF se llaman MPI_10_*) por un error
histórico que ya no se puede corregir en los informes emitidos. El que manda
es el de la configuración, que sale de la carpeta de la que vino el fichero.
"""

from __future__ import annotations

import datetime as dt

import pytest

from src.modules.steriflow.logic.config import AutoclaveConfig
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle
from src.modules.steriflow.logic.sterilization.service import _aplicar_autoclave


def _autoclave(name: str, code: int, report_code: int) -> AutoclaveConfig:
    return AutoclaveConfig(
        name=name,
        ip="10.0.0.1",
        code=code,
        report_code=report_code,
        path_folder=rf"\\{name}\Export",
        local_folder=f"C:/Report_MPI/{name}",
        backup_folder=f"R:/backup/{name}",
        active=True,
    )


@pytest.fixture
def ciclo():
    def _construir(reported_code: int) -> SterilizationCycle:
        return SterilizationCycle(
            autoclave_code=reported_code,
            reported_code=reported_code,
            started_at=dt.datetime(2026, 9, 9, 18, 24, 17),
            source_filename="MPI_10_011_-_TOMATE_PELADO__1KG.pdf",
            source_sha256="",
        )

    return _construir


def test_el_10_que_imprime_la_autoclave8_se_guarda_como_8(ciclo):
    c = ciclo(reported_code=10)

    _aplicar_autoclave(c, _autoclave("AUTOCLAVE8", code=8, report_code=10))

    assert c.autoclave_code == 8
    assert c.autoclave == "AUTOCLAVE8"
    # El número impreso no se pierde: es lo que explica el nombre del fichero.
    assert c.reported_code == 10
    assert not c.needs_review


def test_maquina_que_imprime_su_propio_numero(ciclo):
    c = ciclo(reported_code=6)

    _aplicar_autoclave(c, _autoclave("AUTOCLAVE6", code=6, report_code=6))

    assert c.autoclave_code == 6
    assert not c.needs_review


def test_pdf_traspapelado_en_otra_carpeta_se_marca_para_revision(ciclo):
    """Los 3 informes MPI_10_* que hay hoy en la carpeta de AUTOCLAVE9: se
    guardan como ciclos de la 9 -es de donde salieron- pero marcados, en vez
    de colarse como si fueran suyos."""
    c = ciclo(reported_code=10)

    _aplicar_autoclave(c, _autoclave("AUTOCLAVE9", code=9, report_code=9))

    assert c.autoclave_code == 9
    assert c.needs_review
    assert "El informe dice autoclave 10" in c.review_notes


def test_la_nota_de_revision_no_pisa_las_que_ya_hubiera(ciclo):
    c = ciclo(reported_code=10)
    c.needs_review = True
    c.review_notes = "Fase 2: hora de inicio o fin ilegible"

    _aplicar_autoclave(c, _autoclave("AUTOCLAVE9", code=9, report_code=9))

    assert c.review_notes.startswith("Fase 2: hora de inicio o fin ilegible; ")
    assert "El informe dice autoclave 10" in c.review_notes
