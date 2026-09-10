"""`logic/sterilization/reader.py`: qué fase del informe se lee como la de
esterilización.

Las tablas de aquí son las de informes reales de `C:/Report_MPI`, recortadas a
HISTORIAL MEDIDAS. Cubren los cuatro repartos que aparecen en la planta -la
meseta en la fase 2, en la 3 y en la 4, y el ciclo abortado sin filas-, que es
justo lo que el lector no distinguía cuando iba a buscar la fase 3 fija: en
`011 TOMATE PELADO` guardaba un enfriamiento (97 °C de media) como si fuera la
esterilización.

Se prueba contra el texto ya extraído y no contra un PDF: abrir un informe de
verdad ataría la prueba a pdfplumber y a un fichero que no está en el repo,
y lo que se quiere fijar aquí es la elección de la fila, no la extracción.
"""

from __future__ import annotations

import datetime as dt

import pytest

from src.modules.steriflow.logic.sterilization.models import SterilizationCycle
from src.modules.steriflow.logic.sterilization.reader import _leer_fase_esterilizacion

_CABECERA = """HISTORIAL MEDIDAS
Numero lote MPI 6 003 - PRODUCTO [01/06/2026 01:01:20]
Fecha 01/06/2026 01:55:03
Numero de ciclo 003
Concep. PRODUCTO
Cod. Autoclave 6
Temperatura fin de Temperatura Min. (C) Max. (C)
Fase Type Inicio: Fin: Time phase length fase (C) media (C) temperature temperature
"""

# 003 GUISANTE: tres calentamientos, la meseta es la 3 (el caso que ya
# funcionaba con el número fijo).
MESETA_EN_3 = _CABECERA + """1 Calentam. 01:03:32 01:13:47 00:10:14 109.57 78.36 46.68 109.57
2 Calentam. 01:13:47 01:18:08 00:04:21 128.54 119.14 109.17 128.54
3 Calentam. 01:18:08 01:30:15 00:12:07 128.94 128.66 124.44 129.53
4 Enfriamiento 1 01:30:15 01:35:28 00:05:14 80.42 100.90 80.42 129.03
5 Enfriamiento 1 01:35:28 01:49:02 00:13:33 40.49 56.69 40.49 80.32
6 Forced cool. 1 01:49:02 01:55:02 00:06:00 33.90 36.89 33.90 40.59
01/06/2026 01:55:13 1/1
"""

# 011 TOMATE PELADO 1KG: solo dos calentamientos; la 3 ya es un enfriamiento.
MESETA_EN_2 = _CABECERA + """1 Calentam. 17:23:51 17:36:42 00:12:50 114.56 76.56 34.90 114.56
2 Calentam. 17:36:42 18:16:42 00:40:00 114.86 114.91 113.96 115.36
3 Enfriamiento 1 18:16:42 18:21:42 00:05:00 79.12 96.90 79.12 114.96
4 Enfriamiento 1 18:21:42 18:24:42 00:03:00 60.25 70.21 60.25 80.02
5 Forced cool. 1 18:47:42 19:07:43 00:20:00 28.81 31.70 28.71 38.69
01/06/2026 19:07:50 1/1
"""

# 028 TOMATE PELADO 1l2KG: cuatro calentamientos, la meseta es la 4 y la 3 es
# todavía una rampa intermedia (112 °C de media frente a 115).
MESETA_EN_4 = _CABECERA + """1 Calentam. 23:09:32 23:19:32 00:10:00 99.69 67.90 36.89 99.59
2 Calentam. 23:19:32 23:29:33 00:10:00 109.97 104.84 98.99 110.17
3 Calentam. 23:29:33 23:34:33 00:05:00 115.26 112.42 109.77 115.26
4 Calentam. 23:34:33 23:47:33 00:13:00 115.26 115.16 114.56 115.56
5 Enfriamiento 1 23:47:33 23:52:33 00:05:00 84.41 99.44 84.41 115.56
6 Forced cool. 1 00:06:39 00:23:39 00:17:00 33.60 37.52 33.60 45.48
02/08/2026 00:23:45 1/1
"""

# Ciclo abortado nada más arrancar: la máquina imprime la tabla con guiones.
SIN_FILAS = _CABECERA + """- - - - - - - - -
09/09/2026 23:03:49 1/1
"""

# El informe se corta antes de enfriar (la máquina se paró a mitad).
SIN_ENFRIAMIENTO = _CABECERA + """1 Calentam. 18:53:06 18:58:23 00:05:17 99.69 59.87 17.41 99.69
2 Calentam. 18:58:23 18:59:25 00:01:02 105.79 102.98 99.89 105.79
09/02/2026 19:07:00 1/1
"""

# pdfplumber a veces pega dos temperaturas sin espacio ("128.94128.66"): la
# fila no encaja en el patrón completo y se rescata con el parcial.
TEMPERATURAS_PEGADAS = _CABECERA + """1 Calentam. 01:03:32 01:13:47 00:10:14 109.57 78.36 46.68 109.57
2 Calentam. 01:18:08 01:30:15 00:12:07 128.94128.66 124.44 129.53
3 Enfriamiento 1 01:30:15 01:35:28 00:05:14 80.42 100.90 80.42 129.03
01/06/2026 01:55:13 1/1
"""


@pytest.fixture
def ciclo() -> SterilizationCycle:
    return SterilizationCycle(
        autoclave_code=6,
        started_at=dt.datetime(2026, 6, 1, 1, 1, 20),
        source_filename="informe.pdf",
        source_sha256="",
    )


@pytest.mark.parametrize(
    ("pagina", "fase_esperada", "media_esperada"),
    [
        (MESETA_EN_3, 3, 128.66),
        (MESETA_EN_2, 2, 114.91),
        (MESETA_EN_4, 4, 115.16),
    ],
    ids=["meseta_en_3", "meseta_en_2", "meseta_en_4"],
)
def test_elige_la_ultima_fase_antes_de_enfriar(ciclo, pagina, fase_esperada, media_esperada):
    _leer_fase_esterilizacion([pagina], ciclo)

    assert ciclo.sterilization_phase_number == fase_esperada
    assert ciclo.sterilization_phase_type == "Calentam."
    assert ciclo.sterilization_temp_mean_c == media_esperada
    assert not ciclo.needs_review


def test_guarda_horas_y_duracion_de_la_fase_elegida(ciclo):
    _leer_fase_esterilizacion([MESETA_EN_2], ciclo)

    assert ciclo.sterilization_start_ts == dt.datetime(2026, 6, 1, 17, 36, 42)
    assert ciclo.sterilization_end_ts == dt.datetime(2026, 6, 1, 18, 16, 42)
    assert ciclo.sterilization_duration_s == 40 * 60
    assert ciclo.sterilization_temp_min_c == 113.96
    assert ciclo.sterilization_temp_max_c == 115.36


def test_tabla_sin_filas_marca_revision_y_no_inventa_fase(ciclo):
    _leer_fase_esterilizacion([SIN_FILAS], ciclo)

    assert ciclo.sterilization_phase_number is None
    assert ciclo.sterilization_temp_mean_c is None
    assert ciclo.needs_review
    assert "fila de fase" in ciclo.review_notes


def test_informe_que_no_llega_a_enfriar_usa_la_ultima_y_avisa(ciclo):
    _leer_fase_esterilizacion([SIN_ENFRIAMIENTO], ciclo)

    assert ciclo.sterilization_phase_number == 2
    assert ciclo.needs_review
    assert "no llega a enfriar" in ciclo.review_notes


def test_temperaturas_pegadas_se_separan_sin_perder_la_fila(ciclo):
    _leer_fase_esterilizacion([TEMPERATURAS_PEGADAS], ciclo)

    # La fila pegada sigue contando como fase, así que la meseta sigue siendo
    # la 2 -si se descartara, se elegiría la 1 y el dato saldría de la rampa-.
    assert ciclo.sterilization_phase_number == 2
    assert ciclo.sterilization_temp_end_c == 128.94
    assert ciclo.sterilization_temp_mean_c == 128.66
    assert not ciclo.needs_review


def test_sin_seccion_de_historial_marca_revision(ciclo):
    _leer_fase_esterilizacion(["Otra pagina cualquiera del informe"], ciclo)

    assert ciclo.sterilization_phase_number is None
    assert ciclo.needs_review
