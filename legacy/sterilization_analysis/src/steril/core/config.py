"""Configuracion.

Los valores por defecto viven en codigo (`DEFAULT_SETTINGS`) y el fichero
`settings.json` se regenera si falta o esta corrupto, para que borrarlo nunca
deje la aplicacion inservible.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .settings_schema import validate_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    "paths": {
        "data_dir": str(PROJECT_ROOT / "data"),
        "database_path": str(PROJECT_ROOT / "store" / "steril.sqlite"),
        "programs_source": str(PROJECT_ROOT / "Programas Ferlo.xlsx"),
        "export_dir": str(PROJECT_ROOT / "export"),
    },
    "source": {
        "profile": "ferlo_xlsx",
        "sheet_index": 0,
        "date_column": "Fecha dd/MM/yyyy",
        "time_column": "Hora H:mm:ss",
        "temperature_column": "Valor °C",
        "pressure_column": "Valor bar",
        "legacy_time_column": "Tiempo",
        "round_timestamp_to_second": True,
    },
    "sampling": {
        "nominal_sample_interval_s": 5,
        "data_gap_warning_s": 15,
        "data_gap_critical_s": 60,
    },
    "cycle_detection": {
        "cycle_start_temperature_c": 50.00,
        "cycle_end_temperature_c": 50.00,
        "min_cycle_duration_min": 10.0,
        "min_cycle_peak_temperature_c": 60.0,
        "setpoint_mode_bin_c": 0.1,
        "setpoint_mode_floor_c": 60.0,
    },
    "sterilization_phase": {
        "sterilization_tolerance_c": 0.50,
        "exit_debounce_s": 60,
        "stabilization_window_min": 10.0,
    },
    "acceptance": {
        "acceptance_tolerance_c": 0.50,
        "acceptance_time_tolerance_min": 1.0,
        "max_over_temperature_c": 1.00,
        "max_extra_time_min": 5.0,
    },
    "review": {
        "review_deviation_c": 1.00,
        "plausible_min_temperature_c": 10.0,
        "plausible_max_temperature_c": 150.0,
        "max_temperature_step_c": 10.0,
    },
    "coverage": {
        "min_phase_coverage_pct": 90.0,
        "max_blind_window_s": 300.0,
    },
    "lethality": {
        "enabled": True,
        "official": False,
        "reference_temperature_c": 121.1,
        "z_value_c": 10.0,
        "vp_enabled": True,
        "vp_reference_temperature_c": 93.3,
        "vp_z_value_c": 10.0,
    },
    "maintenance": {
        "purge_keep_margin_min": 10.0,
        "purge_older_than_days": 90,
    },
    "autoclaves": [
        {"id": i, "name": f"Ferlo {i}", "file_pattern": f"Ferlo{i}.xlsx",
         "calibration_offset_c": 0.0, "is_active": True}
        for i in range(1, 6)
    ],
    # Steriflow es un sistema aparte (ver el paquete `steril.steriflow`): sus
    # autoclaves no entran en la lista de arriba porque no comparten ni tablas
    # ni analisis con los de Ferlo.
    "steriflow": {
        "reports_root": r"C:\Report_MPI",
        "file_pattern": "*.pdf",
        "autoclaves": [
            {"code": i, "name": f"Steriflow {i}", "folder": "", "is_active": True}
            for i in range(6, 10)
        ],
    },
    "pizza": {
        "csv_root": str(PROJECT_ROOT / "data" / "pizza"),
        "file_pattern": "*.csv",
    },
}


@dataclass(slots=True)
class Autoclave:
    id: int
    name: str
    file_pattern: str
    calibration_offset_c: float = 0.0
    is_active: bool = True


@dataclass(slots=True)
class SteriflowAutoclave:
    """Un autoclave Steriflow y donde estan sus informes.

    `code` es el numero que imprime la maquina en 'Cod. Autoclave', y es lo que
    empareja el PDF con su autoclave: no es un `Autoclave.id` de Ferlo ni tiene
    por que no coincidir con uno.
    """

    code: int
    name: str
    folder: str = ""
    is_active: bool = True

    def resolve_folder(self, root: Path | str) -> Path:
        """Carpeta de informes de este autoclave.

        Con `folder` vacio se deriva de la raiz como AUTOCLAVE<code>, que es
        como los nombra la maquina. Se admite tambien una ruta propia -relativa
        a la raiz o absoluta- para el caso de que algun autoclave deje sus
        informes en otro sitio.
        """
        if not self.folder.strip():
            return Path(root) / f"AUTOCLAVE{self.code}"
        propia = Path(self.folder.strip())
        return propia if propia.is_absolute() else Path(root) / propia


class Settings:
    """Acceso tipado a settings.json.

    Se accede por seccion (`settings.acceptance["acceptance_tolerance_c"]`) para
    que anadir un umbral no obligue a tocar esta clase.
    """

    def __init__(self, data: dict[str, Any], path: Path | None = None) -> None:
        self._data = data
        self.path = path
        # Avisos (nunca errores) de valores fuera del rango declarado en
        # settings_schema.py: un umbral fuera de rango puede ser una decision
        # deliberada de calidad, asi que se avisa sin bloquear la carga.
        self.validation_warnings: list[str] = validate_settings(data)

    # --- secciones ---
    @property
    def paths(self) -> dict[str, str]:
        return self._data["paths"]

    @property
    def source(self) -> dict[str, Any]:
        return self._data["source"]

    @property
    def sampling(self) -> dict[str, Any]:
        return self._data["sampling"]

    @property
    def cycle_detection(self) -> dict[str, Any]:
        return self._data["cycle_detection"]

    @property
    def sterilization_phase(self) -> dict[str, Any]:
        return self._data["sterilization_phase"]

    @property
    def acceptance(self) -> dict[str, Any]:
        return self._data["acceptance"]

    @property
    def review(self) -> dict[str, Any]:
        return self._data["review"]

    @property
    def coverage(self) -> dict[str, Any]:
        return self._data["coverage"]

    @property
    def lethality(self) -> dict[str, Any]:
        return self._data["lethality"]

    @property
    def maintenance(self) -> dict[str, Any]:
        return self._data["maintenance"]

    @property
    def data_dir(self) -> Path:
        return Path(self.paths["data_dir"])

    @property
    def autoclaves(self) -> list[Autoclave]:
        return [Autoclave(**a) for a in self._data["autoclaves"]]

    def autoclave(self, autoclave_id: int) -> Autoclave | None:
        for a in self.autoclaves:
            if a.id == autoclave_id:
                return a
        return None

    # --- Steriflow (sistema aparte, ver el paquete `steril.steriflow`) ---
    @property
    def steriflow(self) -> dict[str, Any]:
        return self._data["steriflow"]

    @property
    def steriflow_reports_root(self) -> Path:
        return Path(self.steriflow["reports_root"])

    @property
    def steriflow_autoclaves(self) -> list[SteriflowAutoclave]:
        return [SteriflowAutoclave(**a) for a in self.steriflow["autoclaves"]]

    # --- Pizza (sistema aparte, ver el paquete `steril.pizza`) ---
    @property
    def pizza(self) -> dict[str, Any]:
        return self._data["pizza"]

    @property
    def pizza_csv_root(self) -> Path:
        return Path(self.pizza["csv_root"])

    def set_pizza_root(self, value: str) -> None:
        self._data["pizza"]["csv_root"] = value

    def set_steriflow_root(self, value: str) -> None:
        self._data["steriflow"]["reports_root"] = value

    def set_steriflow_autoclaves(self, autoclaves: list[SteriflowAutoclave]) -> None:
        self._data["steriflow"]["autoclaves"] = [
            {"code": a.code, "name": a.name, "folder": a.folder,
             "is_active": a.is_active}
            for a in autoclaves
        ]

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def update_section(self, section: str, values: dict[str, Any]) -> None:
        """Sobrescribe los valores escalares de una seccion (las que describe
        `settings_schema.py`). No valida rangos aqui -eso lo hace
        `validate_settings`, que se vuelve a correr para refrescar
        `validation_warnings`-: guardar un valor fuera de rango es una
        decision del usuario, no un error de programa."""
        self._data[section].update(values)
        self.validation_warnings = validate_settings(self._data)

    def set_path(self, key: str, value: str) -> None:
        self._data["paths"][key] = value

    def set_autoclaves(self, autoclaves: list[Autoclave]) -> None:
        self._data["autoclaves"] = [
            {"id": a.id, "name": a.name, "file_pattern": a.file_pattern,
             "calibration_offset_c": a.calibration_offset_c, "is_active": a.is_active}
            for a in autoclaves
        ]

    def criteria_snapshot(self) -> dict[str, float]:
        """Umbrales que deciden un veredicto.

        Se congela junto a cada ciclo: sin esto, subir manana una tolerancia
        cambiaria en silencio el veredicto de ciclos ya validados.
        """
        snap: dict[str, float] = {}
        for section in ("sterilization_phase", "acceptance", "coverage"):
            snap.update(self._data[section])
        return snap

    def save(self, path: Path | None = None) -> Path:
        target = path or self.path or DEFAULT_SETTINGS_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return target


def _merge_defaults(user: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Completa claves que falten sin pisar las que el usuario haya cambiado.

    Asi anadir un umbral nuevo en una version posterior no obliga a borrar el
    settings.json existente.
    """
    out = copy.deepcopy(defaults)
    for key, value in user.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _merge_defaults(value, out[key])
        else:
            out[key] = value
    return out


def load_settings(path: Path | None = None) -> Settings:
    """Carga settings.json; lo regenera si falta o no es JSON valido."""
    target = Path(path) if path else DEFAULT_SETTINGS_PATH
    if not target.exists():
        settings = Settings(copy.deepcopy(DEFAULT_SETTINGS), target)
        settings.save()
        return settings
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        backup = target.with_suffix(".json.corrupto")
        target.replace(backup)
        settings = Settings(copy.deepcopy(DEFAULT_SETTINGS), target)
        settings.save()
        return settings
    return Settings(_merge_defaults(raw, DEFAULT_SETTINGS), target)
