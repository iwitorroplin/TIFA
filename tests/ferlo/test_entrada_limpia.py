"""La carpeta de entrada queda vacía después de importar
(`logic/ingest/service.py:import_machine`).

La entrada es un buzón transitorio (D1). Antes solo se borraban los `.csv` que
se llegaban a procesar, así que un fichero que no fuera CSV -o uno que fallara
al leerse- se quedaba allí para siempre y volvía a aparecer como pendiente en
cada importación.
"""

from __future__ import annotations

import copy
import datetime as dt
import sqlite3

import pytest

from src.modules.ferlo.logic.config import DEFAULT_SETTINGS, Settings
from src.modules.ferlo.logic.ingest.reader import ENCODING
from src.modules.ferlo.logic.ingest.service import import_machine
from src.modules.ferlo.logic.schema import ensure_tables

MACHINE = "F1"
INICIO = dt.datetime(2026, 8, 1, 6, 0, 0)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ensure_tables(c)
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


def _escribir_csv(settings: Settings, nombre: str, muestras: int = 30) -> None:
    entrada = settings.entrada_dir / MACHINE
    entrada.mkdir(parents=True, exist_ok=True)
    filas = ["Hora\tHora\tTEMP\tPRES", "Fecha dd/MM/yyyy\tHora H:mm:ss\tValor °C\tValor bar"]
    for i in range(muestras):
        momento = INICIO + dt.timedelta(seconds=i * 5)
        filas.append(
            f"{momento:%d/%m/%Y}\t{momento:%H:%M:%S}\t{40 + i * 2},0\t0,000"
        )
    (entrada / nombre).write_text("\n".join(filas) + "\n", encoding=ENCODING)


def test_import_deja_la_entrada_vacia(conn, settings):
    entrada = settings.entrada_dir / MACHINE
    _escribir_csv(settings, "export.csv")
    (entrada / "notas.txt").write_text("apunte del operario", encoding="utf-8")
    (entrada / "export.csv.bak").write_text("copia a medias", encoding="utf-8")

    resumen = import_machine(conn, settings, MACHINE)

    assert list(entrada.iterdir()) == []
    assert entrada.is_dir()  # vacía, pero no desaparecida
    # Los dos que no eran CSV importables se cuentan aparte del CSV que sí lo era.
    assert resumen.leftovers_removed == 2


def test_import_no_toca_subcarpetas(conn, settings):
    """Una subcarpeta ahí dentro la ha puesto una persona: vaciar la entrada
    no es excusa para borrar lo que no son ficheros sueltos."""
    entrada = settings.entrada_dir / MACHINE
    entrada.mkdir(parents=True, exist_ok=True)
    (entrada / "historico").mkdir()
    (entrada / "historico" / "viejo.csv").write_text("x", encoding="utf-8")

    import_machine(conn, settings, MACHINE)

    assert (entrada / "historico" / "viejo.csv").is_file()


def test_import_sin_carpeta_de_entrada_la_crea_vacia(conn, settings):
    resumen = import_machine(conn, settings, MACHINE)

    assert (settings.entrada_dir / MACHINE).is_dir()
    assert resumen.leftovers_removed == 0
    assert resumen.arrivals == []
