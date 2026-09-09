"""Etapa 2 - Normalizacion.

Convierte una `RawTable` en una `Series` lista para analizar:

  * construye el instante desde Fecha + Hora (la columna `Tiempo` del programa
    antiguo NO es fuente: solo comprobacion cruzada),
  * redondea al segundo -los seriales de Excel producen colas como
    `00:12:20.000001` que ensucian las duraciones-,
  * aplica el offset de calibracion del autoclave,
  * detecta huecos, valores ausentes, lecturas imposibles y saltos.

Las incidencias repetidas se agregan por bloques contiguos: 759 celdas vacias
seguidas son un aviso, no 759.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from ..core.config import Autoclave, Settings
from ..core.enums import FindingCode, Severity
from ..core.models import Finding, Series
from .base import RawTable

EXCEL_EPOCH = dt.datetime(1899, 12, 30)

_DATE_FORMATS = (
    "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y",
    "%a %b %d %Y",  # texto tipo 'Fri Jul 31 2026 ...' de reexportaciones
)


class NormalizationError(ValueError):
    """El fichero no tiene la forma minima para poder normalizarse."""


def _to_date(value: Any) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, (int, float)):
        return (EXCEL_EPOCH + dt.timedelta(days=float(value))).date()
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(text[: len(fmt) + 6].strip(), fmt).date()
        except ValueError:
            continue
    # 'Fri Jul 31 2026 02:00:00 GMT+0200 (...)': quedarse con los 4 primeros campos
    partes = text.split()
    if len(partes) >= 4:
        try:
            return dt.datetime.strptime(" ".join(partes[:4]), "%a %b %d %Y").date()
        except ValueError:
            pass
    return None


def _to_seconds(value: Any) -> float | None:
    """Segundos desde medianoche."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        value = value.time()
    if isinstance(value, dt.time):
        return value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1e6
    if isinstance(value, dt.timedelta):
        return value.total_seconds()
    if isinstance(value, (int, float)):
        # fraccion de dia de Excel
        return float(value) * 86400.0 if float(value) < 1 else float(value)
    text = str(value).strip()
    if not text:
        return None
    partes = text.split(":")
    if not 2 <= len(partes) <= 3:
        return None
    try:
        h = int(partes[0])
        m = int(partes[1])
        s = float(partes[2]) if len(partes) == 3 else 0.0
    except ValueError:
        return None
    return h * 3600 + m * 60 + s


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _blocks(indices: list[int]) -> list[tuple[int, int]]:
    """Agrupa indices consecutivos en bloques (inicio, fin)."""
    if not indices:
        return []
    out: list[tuple[int, int]] = []
    inicio = anterior = indices[0]
    for i in indices[1:]:
        if i != anterior + 1:
            out.append((inicio, anterior))
            inicio = i
        anterior = i
    out.append((inicio, anterior))
    return out


def normalize(
    table: RawTable,
    settings: Settings,
    autoclave: Autoclave,
) -> Series:
    src = settings.source
    i_date = table.column_index(src["date_column"], default=0)
    i_time = table.column_index(src["time_column"], default=1)
    i_temp = table.column_index(src["temperature_column"], default=2)
    i_pres = table.column_index(src["pressure_column"], default=3)
    i_legacy = table.column_index(src["legacy_time_column"])
    redondear = bool(src.get("round_timestamp_to_second", True))

    if i_date is None or i_time is None or i_temp is None:
        raise NormalizationError(
            f"{table.source_path.name}: faltan columnas obligatorias. "
            f"Cabecera leida: {table.headers}"
        )

    serie = Series(
        autoclave_id=autoclave.id,
        autoclave_name=autoclave.name,
        source_filename=table.source_path.name,
    )
    findings = serie.findings
    offset = float(autoclave.calibration_offset_c or 0.0)
    rev = settings.review
    t_min = float(rev["plausible_min_temperature_c"])
    t_max = float(rev["plausible_max_temperature_c"])

    sin_fecha = 0
    desfase_legado = 0
    peor_desfase = 0.0

    for n, fila in enumerate(table.rows, start=2):  # fila 1 = cabecera
        fecha = _to_date(fila[i_date])
        segundos = _to_seconds(fila[i_time])
        if fecha is None or segundos is None:
            sin_fecha += 1
            continue

        ts = dt.datetime.combine(fecha, dt.time()) + dt.timedelta(seconds=segundos)
        if redondear:
            ts = (ts + dt.timedelta(seconds=0.5)).replace(microsecond=0)

        if i_legacy is not None:
            legado = _to_float(fila[i_legacy])
            if legado is not None:
                esperado = EXCEL_EPOCH + dt.timedelta(days=legado)
                if redondear:
                    esperado = (esperado + dt.timedelta(seconds=0.5)).replace(microsecond=0)
                desfase = abs((esperado - ts).total_seconds())
                if desfase > 1.0:
                    desfase_legado += 1
                    peor_desfase = max(peor_desfase, desfase)

        temp = _to_float(fila[i_temp])
        if temp is not None:
            temp += offset
        serie.ts.append(ts)
        serie.temperature_c.append(temp)
        serie.pressure_bar.append(_to_float(fila[i_pres]) if i_pres is not None else None)

    if sin_fecha:
        findings.append(Finding(
            FindingCode.UNPARSABLE_ROW, Severity.ERROR,
            f"{sin_fecha} filas descartadas: fecha u hora ilegibles",
            value=float(sin_fecha),
        ))
    if desfase_legado:
        findings.append(Finding(
            FindingCode.LEGACY_TIME_MISMATCH, Severity.REVIEW,
            f"La columna '{src['legacy_time_column']}' no coincide con Fecha+Hora en "
            f"{desfase_legado} filas (peor desfase {peor_desfase:.1f} s)",
            value=peor_desfase,
        ))
    if not serie.ts:
        raise NormalizationError(f"{table.source_path.name}: ninguna fila utilizable")

    _validar_tiempos(serie, settings)
    _validar_valores(serie, t_min, t_max, float(rev["max_temperature_step_c"]))
    if offset:
        # Queda registrado: un informe con temperaturas corregidas y sin decirlo
        # deja de ser trazable.
        findings.append(Finding(
            FindingCode.CALIBRATION_APPLIED, Severity.INFO,
            f"Aplicado offset de calibracion {offset:+.2f} °C a {autoclave.name}",
            value=offset,
        ))
    return serie


def _validar_tiempos(serie: Series, settings: Settings) -> None:
    aviso = float(settings.sampling["data_gap_warning_s"])
    critico = float(settings.sampling["data_gap_critical_s"])
    findings = serie.findings
    desorden = 0
    duplicados = 0

    for i in range(1, len(serie.ts)):
        delta = (serie.ts[i] - serie.ts[i - 1]).total_seconds()
        if delta == 0:
            duplicados += 1
        elif delta < 0:
            desorden += 1
        elif delta > aviso:
            sev = Severity.ERROR if delta > critico else Severity.REVIEW
            findings.append(Finding(
                FindingCode.DATA_GAP, sev,
                f"Hueco de {delta:.0f} s sin datos",
                ts=serie.ts[i - 1], value=delta,
            ))
    if duplicados:
        findings.append(Finding(
            FindingCode.DUPLICATE_TIMESTAMP, Severity.REVIEW,
            f"{duplicados} instantes duplicados", value=float(duplicados),
        ))
    if desorden:
        findings.append(Finding(
            FindingCode.OUT_OF_ORDER, Severity.ERROR,
            f"{desorden} instantes fuera de orden", value=float(desorden),
        ))


def _validar_valores(serie: Series, t_min: float, t_max: float, paso_max: float) -> None:
    findings = serie.findings
    temps = serie.temperature_c

    for inicio, fin in _blocks([i for i, v in enumerate(temps) if v is None]):
        dur = (serie.ts[fin] - serie.ts[inicio]).total_seconds() / 60.0
        findings.append(Finding(
            FindingCode.MISSING_TEMPERATURE, Severity.REVIEW,
            f"Temperatura ausente en {fin - inicio + 1} filas ({dur:.1f} min)",
            ts=serie.ts[inicio], value=float(fin - inicio + 1),
        ))
    for inicio, fin in _blocks([i for i, v in enumerate(serie.pressure_bar) if v is None]):
        findings.append(Finding(
            FindingCode.MISSING_PRESSURE, Severity.INFO,
            f"Presion ausente en {fin - inicio + 1} filas",
            ts=serie.ts[inicio], value=float(fin - inicio + 1),
        ))

    for i, v in enumerate(temps):
        if v is not None and not (t_min <= v <= t_max):
            findings.append(Finding(
                FindingCode.IMPLAUSIBLE_READING, Severity.REVIEW,
                f"Lectura fuera de rango plausible: {v:.1f} °C",
                ts=serie.ts[i], value=v,
            ))

    anterior: float | None = None
    for i, v in enumerate(temps):
        if v is None:
            anterior = None
            continue
        if anterior is not None and abs(v - anterior) > paso_max:
            findings.append(Finding(
                FindingCode.TEMPERATURE_STEP, Severity.REVIEW,
                f"Salto de {v - anterior:+.1f} °C entre muestras consecutivas",
                ts=serie.ts[i], value=v - anterior,
            ))
        anterior = v
