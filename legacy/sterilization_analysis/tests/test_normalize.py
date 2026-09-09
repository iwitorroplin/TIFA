from __future__ import annotations

import datetime as dt

from steril.core.enums import FindingCode, Severity
from steril.io.base import RawTable
from steril.io.normalize import EXCEL_EPOCH, normalize

CABECERA = ["Fecha dd/MM/yyyy", "Hora H:mm:ss", "Valor °C", "Valor bar"]


def _tabla(filas, cabecera=CABECERA):
    from pathlib import Path
    return RawTable(Path("test.xlsx"), "Hoja1", list(cabecera), filas, "sha")


def _codigos(serie):
    return {f.code for f in serie.findings}


def test_fecha_como_objeto_y_hora_como_texto(settings, autoclave):
    """Forma real: openpyxl devuelve datetime en la fecha y str en la hora."""
    filas = [(dt.datetime(2026, 7, 31), "05:14:18", 34.3, 0.014),
             (dt.datetime(2026, 7, 31), "05:14:20", 34.3, 0.014)]
    serie = normalize(_tabla(filas), settings, autoclave)
    assert serie.ts[0] == dt.datetime(2026, 7, 31, 5, 14, 18)
    assert (serie.ts[1] - serie.ts[0]).total_seconds() == 2
    assert serie.temperature_c == [34.3, 34.3]


def test_fecha_como_serial_de_excel(settings, autoclave):
    filas = [(46234, "05:14:18", 34.3, 0.014)]
    serie = normalize(_tabla(filas), settings, autoclave)
    assert serie.ts[0] == dt.datetime(2026, 7, 31, 5, 14, 18)


def test_fecha_como_texto_reexportado(settings, autoclave):
    """Una reexportacion puede convertir la fecha a texto en ingles."""
    filas = [("Fri Jul 31 2026 02:00:00 GMT+0200 (Central European Summer Time)",
              "05:14:18", 34.3, 0.014)]
    serie = normalize(_tabla(filas), settings, autoclave)
    assert serie.ts[0].date() == dt.date(2026, 7, 31)


def test_cruce_de_medianoche(settings, autoclave):
    filas = [(46234, "23:59:55", 40.0, 0.0), (46235, "00:00:00", 40.0, 0.0)]
    serie = normalize(_tabla(filas), settings, autoclave)
    assert (serie.ts[1] - serie.ts[0]).total_seconds() == 5


def test_redondeo_al_segundo(settings, autoclave):
    """El serial de Excel produce colas como 00:12:20.000001."""
    serial = 46234 + (12 * 3600 + 20) / 86400 + 1e-11
    filas = [(46234, (EXCEL_EPOCH + dt.timedelta(days=serial)).time(), 40.0, 0.0)]
    serie = normalize(_tabla(filas), settings, autoclave)
    assert serie.ts[0].microsecond == 0


def test_columna_tiempo_legada_solo_se_comprueba(settings, autoclave):
    cab = CABECERA + ["Tiempo"]
    filas = [(46234, "05:14:18", 34.3, 0.014, 46234.218263888892)]
    serie = normalize(_tabla(filas, cab), settings, autoclave)
    assert serie.ts[0] == dt.datetime(2026, 7, 31, 5, 14, 18)
    assert FindingCode.LEGACY_TIME_MISMATCH not in _codigos(serie)


def test_columna_tiempo_discrepante_avisa(settings, autoclave):
    cab = CABECERA + ["Tiempo"]
    filas = [(46234, "05:14:18", 34.3, 0.014, 46234.5)]
    serie = normalize(_tabla(filas, cab), settings, autoclave)
    assert FindingCode.LEGACY_TIME_MISMATCH in _codigos(serie)
    # la fuente sigue siendo Fecha+Hora, no la columna legada
    assert serie.ts[0] == dt.datetime(2026, 7, 31, 5, 14, 18)


def test_hueco_de_datos(settings, autoclave):
    filas = [(46234, "05:00:00", 40.0, 0.0), (46234, "05:02:00", 40.0, 0.0)]
    serie = normalize(_tabla(filas), settings, autoclave)
    huecos = [f for f in serie.findings if f.code is FindingCode.DATA_GAP]
    assert len(huecos) == 1
    assert huecos[0].severity is Severity.ERROR  # 120 s supera el critico


def test_valores_ausentes_se_agregan_por_bloques(settings, autoclave):
    filas = [(46234, f"05:00:{i:02d}", None if 2 <= i <= 8 else 40.0, 0.0)
             for i in range(0, 12)]
    serie = normalize(_tabla(filas), settings, autoclave)
    faltan = [f for f in serie.findings if f.code is FindingCode.MISSING_TEMPERATURE]
    assert len(faltan) == 1          # un aviso por bloque, no siete
    assert faltan[0].value == 7.0


def test_lectura_imposible_y_salto(settings, autoclave):
    filas = [(46234, "05:00:00", 40.0, 0.0), (46234, "05:00:05", 3.4, 0.0)]
    serie = normalize(_tabla(filas), settings, autoclave)
    assert FindingCode.IMPLAUSIBLE_READING in _codigos(serie)
    assert FindingCode.TEMPERATURE_STEP in _codigos(serie)


def test_offset_de_calibracion_se_aplica_y_se_registra(settings, autoclave):
    autoclave.calibration_offset_c = 0.3
    filas = [(46234, "05:00:00", 116.9, 0.0)]
    serie = normalize(_tabla(filas), settings, autoclave)
    assert serie.temperature_c[0] == 117.2
    assert FindingCode.CALIBRATION_APPLIED in _codigos(serie)
