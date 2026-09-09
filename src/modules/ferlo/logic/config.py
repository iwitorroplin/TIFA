"""Umbrales del analisis de Ferlo: lee y escribe `config/appConfig/ferloConfig.yaml`.

Fase 3 del port (decision D7): sustituye al `Settings` en memoria de la
Fase 2 -mismo acceso por seccion, para que `logic/analysis/*` no tuviera que
tocarse dos veces- por uno respaldado en disco, siguiendo el patron de
`src/shared/config/manager.py` que ya usan Steriflow y la app. El default
versionado vive en `config/appConfigDefault/ferloConfig.default.yaml`.

`SETTINGS_SCHEMA` es la parte de `core/settings_schema.py` (de
`sterilization_analysis`) que sigue haciendo falta: seccion, etiqueta, unidad
y rango de cada campo, para que la pestana de ajustes (Fase 4) se construya
sola en vez de a mano. Recortado a los campos que `logic/analysis/` usa de
verdad -sin `coverage` ni `lethality`, que ya no deciden nada (D6)-. `paths`
no esta en el esquema de campos: son rutas de carpeta (D1), se editan como
tal en Fase 4, no con un `QDoubleSpinBox`.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterator, Literal

from src.shared.config.manager import ensure_config_file, load_config, save_config
from src.shared.config.paths import config_path as _config_path

_MODULE = "ferlo"


def config_path():
    """Ruta de `config/appConfig/ferloConfig.yaml` (exista o no todavia)."""
    return _config_path(_MODULE)

DEFAULT_SETTINGS: dict[str, Any] = {
    # D1: la entrada es un buzon transitorio (el operario deja aqui lo que
    # exporte, por maquina); el archivo es el mensual que TIFA mantiene y al
    # que solo se le anade. Relativas a la raiz del programa, como el resto
    # de rutas de TIFA (ver src/shared/paths.py:resolve_path).
    "paths": {
        "entrada": "data/ferlo/entrada",
        "archivo": "data/ferlo/archivo",
    },
    "sampling": {
        "nominal_sample_interval_s": 5,
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
    },
    "review": {
        "review_deviation_c": 1.00,
    },
}


Kind = Literal["float", "int"]


@dataclass(slots=True, frozen=True)
class FieldSpec:
    section: str
    key: str
    label: str
    kind: Kind
    unit: str = ""
    minimum: float | None = None
    maximum: float | None = None
    decimals: int = 2
    help: str = ""


@dataclass(slots=True, frozen=True)
class SectionSpec:
    key: str
    label: str
    fields: tuple[FieldSpec, ...]


SETTINGS_SCHEMA: tuple[SectionSpec, ...] = (
    SectionSpec("sampling", "Muestreo", (
        FieldSpec("sampling", "nominal_sample_interval_s", "Intervalo nominal de muestra",
                  "float", "s", 1.0, 300.0, 0,
                  "Cada cuanto se espera una lectura. Es la base para topar huecos."),
    )),
    SectionSpec("cycle_detection", "Deteccion de ciclos", (
        FieldSpec("cycle_detection", "cycle_start_temperature_c", "Temperatura de inicio",
                  "float", "°C", 0.0, 150.0, 2, "Un ciclo empieza cuando la temperatura la alcanza."),
        FieldSpec("cycle_detection", "cycle_end_temperature_c", "Temperatura de fin",
                  "float", "°C", 0.0, 150.0, 2, "Un ciclo termina cuando la temperatura baja de este valor."),
        FieldSpec("cycle_detection", "min_cycle_duration_min", "Duracion minima",
                  "float", "min", 0.0, 300.0, 1, "Ciclos mas cortos se descartan como ruido."),
        FieldSpec("cycle_detection", "min_cycle_peak_temperature_c", "Pico minimo",
                  "float", "°C", 0.0, 150.0, 1, "Ciclos que no llegan a este pico se descartan."),
        FieldSpec("cycle_detection", "setpoint_mode_bin_c", "Resolucion de la moda",
                  "float", "°C", 0.01, 5.0, 2,
                  "Bin de redondeo para estimar la consigna por moda de la meseta."),
        FieldSpec("cycle_detection", "setpoint_mode_floor_c", "Suelo de la meseta",
                  "float", "°C", 0.0, 150.0, 1,
                  "Por debajo de este valor se considera rampa o enfriamiento, no meseta."),
    )),
    SectionSpec("sterilization_phase", "Fase de esterilizacion", (
        FieldSpec("sterilization_phase", "sterilization_tolerance_c", "Tolerancia de banda",
                  "float", "°C", 0.0, 10.0, 2,
                  "Margen bajo consigna que sigue contando como dentro de la fase."),
        FieldSpec("sterilization_phase", "exit_debounce_s", "Antirrebote de salida",
                  "float", "s", 0.0, 600.0, 0,
                  "Una bajada bajo la banda solo termina la fase si persiste mas de esto."),
        FieldSpec("sterilization_phase", "stabilization_window_min", "Ventana de estabilizacion",
                  "float", "min", 0.0, 60.0, 1,
                  "Tramo inicial de la fase excluido de la media estable y de las desviaciones."),
    )),
    SectionSpec("acceptance", "Criterios de aceptacion", (
        FieldSpec("acceptance", "acceptance_tolerance_c", "Tolerancia de temperatura",
                  "float", "°C", 0.0, 10.0, 2,
                  "Cuanto puede bajar la media (oficial y estable) de la consigna sin dejar "
                  "de ser conforme."),
        FieldSpec("acceptance", "acceptance_time_tolerance_min", "Tolerancia de tiempo",
                  "float", "min", 0.0, 30.0, 1,
                  "Cuanto puede faltar de duracion sin dejar de ser conforme."),
    )),
    SectionSpec("review", "Revision", (
        FieldSpec("review", "review_deviation_c", "Desviacion a revisar", "float", "°C", 0.0, 10.0, 2,
                  "Desviacion sobre consigna, fuera de la ventana de estabilizacion, que marca REVISAR."),
    )),
)


def iter_fields() -> Iterator[tuple[SectionSpec, FieldSpec]]:
    for seccion in SETTINGS_SCHEMA:
        for campo in seccion.fields:
            yield seccion, campo


def validate_settings(data: dict) -> list[str]:
    """Avisos (nunca errores) de valores fuera del rango declarado.

    No modifica `data` ni impide cargarlo: un valor fuera de rango puede ser
    una decision deliberada, no un dato corrupto.
    """
    avisos: list[str] = []
    for seccion, campo in iter_fields():
        valor = data.get(seccion.key, {}).get(campo.key)
        if valor is None:
            continue
        if campo.minimum is not None and valor < campo.minimum:
            avisos.append(
                f"{seccion.label} / {campo.label}: {valor} por debajo del minimo {campo.minimum}"
            )
        if campo.maximum is not None and valor > campo.maximum:
            avisos.append(
                f"{seccion.label} / {campo.label}: {valor} por encima del maximo {campo.maximum}"
            )
    return avisos


class Settings:
    """Acceso tipado a los umbrales, por seccion.

    `settings.acceptance["acceptance_tolerance_c"]` en vez de atributos
    sueltos, para que anadir un umbral no obligue a tocar esta clase -ni
    `logic/analysis/*`, que solo conoce esta interfaz-.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self.validation_warnings: list[str] = validate_settings(data)

    @property
    def paths(self) -> dict[str, Any]:
        return self._data["paths"]

    @property
    def entrada_dir(self):
        from src.shared.paths import resolve_path
        return resolve_path(self.paths["entrada"])

    @property
    def archivo_dir(self):
        from src.shared.paths import resolve_path
        return resolve_path(self.paths["archivo"])

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

    def criteria_snapshot(self) -> dict[str, float]:
        """Umbrales que deciden un veredicto.

        Se congela junto a cada ciclo: sin esto, subir manana una tolerancia
        cambiaria en silencio el veredicto de ciclos ya validados.
        """
        snap: dict[str, float] = {}
        for section in ("sterilization_phase", "acceptance"):
            snap.update(self._data[section])
        return snap

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)


def default_settings() -> Settings:
    """Umbrales por defecto, sin tocar disco. Para tests y para el primer
    arranque antes de que exista `ferloConfig.yaml`."""
    return Settings(copy.deepcopy(DEFAULT_SETTINGS))


def _merge_defaults(user: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Completa claves que falten sin pisar las que el usuario haya cambiado.

    Asi anadir un umbral nuevo en una version posterior no obliga a borrar el
    ferloConfig.yaml existente.
    """
    out = copy.deepcopy(defaults)
    for key, value in user.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _merge_defaults(value, out[key])
        else:
            out[key] = value
    return out


def load_settings() -> Settings:
    ensure_config_file(_MODULE)
    raw = load_config(_MODULE)
    return Settings(_merge_defaults(raw, DEFAULT_SETTINGS))


def save_settings(settings: Settings) -> None:
    save_config(_MODULE, settings.as_dict())
