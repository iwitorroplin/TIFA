"""Orquestacion de las tres etapas.

    importar -> normalizar -> analizar

Este modulo es el unico punto que la UI necesitara llamar. No importa Qt, igual
que el resto del nucleo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..analysis.metrics import compute_metrics
from ..analysis.phases import detect_phases
from ..analysis.segmentation import segment
from ..analysis.validation import validate
from ..core.config import Autoclave, Settings
from ..core.models import CycleResult, Series, SterilizationProgram
from ..io.base import get_reader
from ..io.normalize import normalize


@dataclass(slots=True)
class FileAnalysis:
    autoclave: Autoclave
    series: Series
    cycles: list[CycleResult]
    source_sha256: str


def analyze_file(
    path: Path,
    autoclave: Autoclave,
    settings: Settings,
    program: SterilizationProgram | None = None,
) -> FileAnalysis:
    reader = get_reader(settings.source["profile"])
    table = reader.read(path, sheet_index=settings.source.get("sheet_index", 0))
    serie = normalize(table, settings, autoclave)
    cycles = analyze_series(serie, settings, program)
    return FileAnalysis(autoclave, serie, cycles, table.source_sha256)


def analyze_series(
    serie: Series,
    settings: Settings,
    program: SterilizationProgram | None = None,
) -> list[CycleResult]:
    cycles = segment(serie, settings)
    for cycle in cycles:
        assign(serie, cycle, settings, program)
    return cycles


def assign(
    serie: Series,
    cycle: CycleResult,
    settings: Settings,
    program: SterilizationProgram | None,
) -> CycleResult:
    """Evalua un ciclo, con o sin programa asignado.

    Sin programa se usa la consigna medida, de modo que las fases y las metricas
    puedan verse antes de asignar; el estado queda en UNASSIGNED y no se emite
    ningun veredicto de conformidad.
    """
    if program is not None:
        cycle.program_code = program.code
        cycle.target_temperature_c = program.target_temperature_c
        cycle.target_time_min = program.target_time_min
        cycle.evaluation_setpoint_c = program.target_temperature_c
    else:
        cycle.program_code = None
        cycle.target_temperature_c = None
        cycle.target_time_min = None
        cycle.evaluation_setpoint_c = cycle.measured_setpoint_c

    cycle.findings.clear()
    cycle.phases, dips = detect_phases(
        serie, cycle, cycle.evaluation_setpoint_c, settings
    )
    compute_metrics(serie, cycle, settings)
    validate(serie, cycle, settings, dips)
    return cycle


def discover_files(settings: Settings) -> list[tuple[Autoclave, Path]]:
    """Empareja cada autoclave con su fichero en la carpeta de datos."""
    carpeta = settings.data_dir
    encontrados: list[tuple[Autoclave, Path]] = []
    for autoclave in settings.autoclaves:
        if not autoclave.is_active:
            continue
        for ruta in sorted(carpeta.glob(autoclave.file_pattern)):
            encontrados.append((autoclave, ruta))
    return encontrados
