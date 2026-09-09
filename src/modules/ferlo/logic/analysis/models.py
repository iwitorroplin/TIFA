"""Modelos y enumeraciones del dominio de analisis de Ferlo.

Portado de `sterilization_analysis` (Fase 2 del port a TIFA) sin tocar una
linea salvo un recorte deliberado: `CycleResult` no lleva `lethality_f0_min`
ni `lethality_vp_min`. F0 y VP quedan fuera del calculo, del esquema y de la
interfaz hasta que se pidan -el codigo original sigue en
`legacy/sterilization_analysis/` mientras ese repo exista-.

Nomenclatura: ingles, snake_case, sufijo de unidad siempre (_c, _bar, _s, _min).
Ningun modulo de este paquete importa Qt.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
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


class FindingCode(str, Enum):
    """Codigos estables: se guardan en base de datos, no se renombran."""

    # --- analisis ---
    DIP_BELOW_BAND = "dip_below_band"
    DEVIATION_AFTER_STABILIZATION = "deviation_after_stabilization"
    DATA_GAP_IN_PHASE = "data_gap_in_phase"
    UNDER_TEMPERATURE = "under_temperature"
    UNDER_TIME = "under_time"
    INCOMPLETE_CYCLE = "incomplete_cycle"
    NO_PLATEAU = "no_plateau"

    # DATA_GAP: no lo emite nada de aqui -lo emitira logic/ingest/normalize.py
    # en la Fase 1-, pero `_heredar_incidencias` (validate.py) ya compara
    # contra el, asi que tiene que existir antes de que exista quien lo cree.
    DATA_GAP = "data_gap"


@dataclass(slots=True)
class Finding:
    """Incidencia detectada. `ts` es None cuando afecta al fichero entero."""

    code: FindingCode
    severity: Severity
    message: str
    ts: dt.datetime | None = None
    value: float | None = None

    def __str__(self) -> str:
        marca = self.ts.strftime("%d/%m %H:%M:%S") if self.ts else "-"
        return f"[{self.severity.value}] {marca} {self.code.value}: {self.message}"


@dataclass(slots=True)
class SterilizationProgram:
    """Programa de consigna: solo lo que el analisis necesita para evaluar un
    ciclo -codigo, temperatura y tiempo objetivo, y si esta activo-."""

    code: int
    target_temperature_c: float
    target_time_min: float
    is_active: bool = True

    @property
    def display_code(self) -> str:
        return f"{self.code:02d}"

    @property
    def display_name(self) -> str:
        return f"{self.target_temperature_c:.0f} °C / {self.target_time_min:.0f} min"


@dataclass(slots=True)
class Series:
    """Serie normalizada de un autoclave.

    Listas paralelas en vez de lista de objetos: el analisis recorre indices y
    esto evita construir ~13.500 objetos por fichero y dia.
    """

    autoclave_id: int
    autoclave_name: str
    source_filename: str
    ts: list[dt.datetime] = field(default_factory=list)
    temperature_c: list[float | None] = field(default_factory=list)
    pressure_bar: list[float | None] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.ts)

    @property
    def first_ts(self) -> dt.datetime | None:
        return self.ts[0] if self.ts else None

    @property
    def last_ts(self) -> dt.datetime | None:
        return self.ts[-1] if self.ts else None


@dataclass(slots=True)
class PhaseResult:
    """Resultado de una fase.

    El start/end vive aqui, en el resultado, no en los umbrales de configuracion.
    """

    phase: Phase
    start_index: int
    end_index: int
    start_ts: dt.datetime
    end_ts: dt.datetime
    mean_temperature_c: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None

    @property
    def duration_s(self) -> float:
        return (self.end_ts - self.start_ts).total_seconds()

    @property
    def duration_min(self) -> float:
        return self.duration_s / 60.0


@dataclass(slots=True)
class CycleResult:
    """Un ciclo detectado y, si tiene programa asignado, evaluado."""

    autoclave_id: int
    autoclave_name: str
    start_index: int
    end_index: int
    start_ts: dt.datetime
    end_ts: dt.datetime

    # --- etapa 3a: segmentacion, sin saber el programa ---
    measured_setpoint_c: float = 0.0
    peak_temperature_c: float = 0.0

    # Consigna usada para delimitar la fase. Es la del programa cuando hay uno
    # asignado y la medida (`measured_setpoint_c`) mientras no lo hay, de modo
    # que un ciclo pueda verse antes de asignarle programa.
    evaluation_setpoint_c: float = 0.0

    # --- etapa 3b/3c: requieren programa asignado ---
    program_code: int | None = None
    target_temperature_c: float | None = None
    target_time_min: float | None = None
    phases: dict[Phase, PhaseResult] = field(default_factory=dict)

    mean_temperature_c: float | None = None
    mean_stable_temperature_c: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    time_below_setpoint_min: float | None = None
    time_deviation_min: float | None = None
    extra_time_min: float | None = None

    # cobertura de datos de la fase de esterilizacion (ver analysis/coverage.py):
    # cuanto de su duracion esta respaldada por lecturas de fiar. Se calcula y
    # se muestra, pero no decide el veredicto por si sola (ver validate.py).
    coverage_pct: float | None = None
    max_blind_window_s: float | None = None
    uncovered_min: float | None = None

    status: CycleStatus = CycleStatus.UNASSIGNED
    findings: list[Finding] = field(default_factory=list)
    criteria: dict[str, float] = field(default_factory=dict)

    @property
    def duration_min(self) -> float:
        return (self.end_ts - self.start_ts).total_seconds() / 60.0

    @property
    def sterilization(self) -> PhaseResult | None:
        return self.phases.get(Phase.STERILIZATION)

    @property
    def sterilization_duration_min(self) -> float | None:
        ph = self.sterilization
        return ph.duration_min if ph else None

    @property
    def come_up_time_min(self) -> float | None:
        ph = self.phases.get(Phase.HEATING)
        return ph.duration_min if ph else None

    def has(self, severity: Severity) -> bool:
        return any(f.severity is severity for f in self.findings)
