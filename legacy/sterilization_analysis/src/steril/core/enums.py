"""Enumeraciones del dominio.

Se usan `str, Enum` para que el valor serialice directamente a JSON y a SQLite
sin conversiones intermedias.
"""

from enum import Enum


class Phase(str, Enum):
    HEATING = "heating"
    STERILIZATION = "sterilization"
    COOLING = "cooling"


class CycleStatus(str, Enum):
    OK = "ok"
    REVIEW = "review"
    NON_CONFORMING = "non_conforming"
    INCOMPLETE = "incomplete"
    UNASSIGNED = "unassigned"


class Severity(str, Enum):
    INFO = "info"
    REVIEW = "review"
    ERROR = "error"


class ManualVerdict(str, Enum):
    """Veredicto que decide una persona, aparte del `status` calculado.

    No sustituye a `CycleStatus`: se guarda en su propia columna para que quede
    trazable que dijo el sistema y que decidio la persona. Ver
    `CycleRow.effective_status`.
    """

    NONE = "none"
    CONFORMING = "conforming"
    NON_CONFORMING = "non_conforming"


class FindingCode(str, Enum):
    """Codigos estables: se guardan en base de datos, no se renombran."""

    # --- normalizacion (etapa 2) ---
    MISSING_TEMPERATURE = "missing_temperature"
    MISSING_PRESSURE = "missing_pressure"
    IMPLAUSIBLE_READING = "implausible_reading"
    TEMPERATURE_STEP = "temperature_step"
    DATA_GAP = "data_gap"
    OUT_OF_ORDER = "out_of_order"
    DUPLICATE_TIMESTAMP = "duplicate_timestamp"
    LEGACY_TIME_MISMATCH = "legacy_time_mismatch"
    UNPARSABLE_ROW = "unparsable_row"
    CALIBRATION_APPLIED = "calibration_applied"

    # --- analisis (etapa 3) ---
    DIP_BELOW_BAND = "dip_below_band"
    DEVIATION_AFTER_STABILIZATION = "deviation_after_stabilization"
    DATA_GAP_IN_PHASE = "data_gap_in_phase"
    UNDER_TEMPERATURE = "under_temperature"
    OVER_TEMPERATURE = "over_temperature"
    UNDER_TIME = "under_time"
    OVER_TIME = "over_time"
    INCOMPLETE_CYCLE = "incomplete_cycle"
    NO_PLATEAU = "no_plateau"
    LOW_PHASE_COVERAGE = "low_phase_coverage"
    BLIND_WINDOW_IN_PHASE = "blind_window_in_phase"
    INTERPOLATED_SAMPLES = "interpolated_samples"
