"""Esquema declarativo de `settings.json`.

Cada variable se describe una sola vez aqui: seccion, clave, etiqueta en
espanol, unidad, tipo, rango y ayuda. `ui/dialogs/settings_dialog.py` recorre
este esquema para construirse solo (una pestana por seccion, un
`QDoubleSpinBox`/`QSpinBox`/`QCheckBox` por campo), y `config.load_settings`
lo usa para avisar -sin bloquear la carga- de valores fuera de rango. Anadir
un umbral nuevo es una linea aqui, no un widget escrito a mano.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal

Kind = Literal["float", "int", "bool"]


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
                  "Cada cuanto se espera una lectura. Es la base para topar huecos y letalidad."),
        FieldSpec("sampling", "data_gap_warning_s", "Aviso de hueco", "float", "s", 1.0, 3600.0, 0,
                  "Hueco sin datos a partir del cual se marca REVISAR."),
        FieldSpec("sampling", "data_gap_critical_s", "Hueco critico", "float", "s", 1.0, 7200.0, 0,
                  "Hueco sin datos a partir del cual se marca ERROR."),
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
                  "Cuanto puede bajar la media de la consigna sin dejar de ser conforme."),
        FieldSpec("acceptance", "acceptance_time_tolerance_min", "Tolerancia de tiempo",
                  "float", "min", 0.0, 30.0, 1,
                  "Cuanto puede faltar de duracion sin dejar de ser conforme."),
        FieldSpec("acceptance", "max_over_temperature_c", "Exceso maximo de temperatura",
                  "float", "°C", 0.0, 20.0, 2,
                  "Cuanto puede superar la media a la consigna sin dejar de ser conforme."),
        FieldSpec("acceptance", "max_extra_time_min", "Tiempo extra maximo",
                  "float", "min", 0.0, 60.0, 1,
                  "Cuanto puede alargarse la fase sin dejar de ser conforme."),
    )),
    SectionSpec("review", "Revision", (
        FieldSpec("review", "review_deviation_c", "Desviacion a revisar", "float", "°C", 0.0, 10.0, 2,
                  "Desviacion sobre consigna, fuera de la ventana de estabilizacion, que marca REVISAR."),
        FieldSpec("review", "plausible_min_temperature_c", "Temperatura minima plausible",
                  "float", "°C", -50.0, 50.0, 1, "Lecturas por debajo se marcan como implausibles."),
        FieldSpec("review", "plausible_max_temperature_c", "Temperatura maxima plausible",
                  "float", "°C", 50.0, 300.0, 1, "Lecturas por encima se marcan como implausibles."),
        FieldSpec("review", "max_temperature_step_c", "Salto maximo entre muestras",
                  "float", "°C", 0.0, 50.0, 1,
                  "Diferencia entre dos lecturas consecutivas que se marca como salto sospechoso."),
    )),
    SectionSpec("coverage", "Cobertura de datos", (
        FieldSpec("coverage", "min_phase_coverage_pct", "Cobertura minima", "float", "%", 0.0, 100.0, 1,
                  "Por debajo de esto, la esterilizacion se marca A REVISAR por falta de datos."),
        FieldSpec("coverage", "max_blind_window_s", "Ventana ciega maxima", "float", "s", 0.0, 7200.0, 0,
                  "Tramo continuo sin lectura de fiar dentro de la fase que marca NO CONFORME."),
    )),
    SectionSpec("lethality", "Letalidad", (
        FieldSpec("lethality", "enabled", "Calcular F0", "bool",
                  help="F0 es orientativo: se calcula sobre el sensor de camara, no el punto frio del producto."),
        FieldSpec("lethality", "official", "F0 oficial", "bool",
                  help="Si F0 se usa como criterio de aceptacion en este sitio (hoy es informativo)."),
        FieldSpec("lethality", "reference_temperature_c", "Temperatura de referencia F0",
                  "float", "°C", 50.0, 150.0, 1,
                  "Tref de la formula de F0 (121,1 °C, la referencia clasica de esterilizacion por vapor)."),
        FieldSpec("lethality", "z_value_c", "Valor z de F0", "float", "°C", 1.0, 50.0, 1,
                  "Sensibilidad termica de la formula de F0."),
        FieldSpec("lethality", "vp_enabled", "Calcular VP", "bool",
                  help="VP usa como referencia el vapor de agua a 93,3 °C (ISO 11138-1:2017)."),
        FieldSpec("lethality", "vp_reference_temperature_c", "Temperatura de referencia VP",
                  "float", "°C", 50.0, 150.0, 1, "Tref de la formula de VP."),
        FieldSpec("lethality", "vp_z_value_c", "Valor z de VP", "float", "°C", 1.0, 50.0, 1,
                  "Sensibilidad termica de la formula de VP."),
    )),
    SectionSpec("maintenance", "Mantenimiento", (
        FieldSpec("maintenance", "purge_keep_margin_min", "Margen a conservar",
                  "float", "min", 0.0, 120.0, 1,
                  "Margen de contexto alrededor de cada ciclo guardado que la purga nunca borra."),
        FieldSpec("maintenance", "purge_older_than_days", "Antiguedad minima",
                  "float", "dias", 0.0, 3650.0, 0,
                  "La purga solo borra muestras mas antiguas que esto."),
    )),
)


def iter_fields() -> Iterator[tuple[SectionSpec, FieldSpec]]:
    for seccion in SETTINGS_SCHEMA:
        for campo in seccion.fields:
            yield seccion, campo


def validate_settings(data: dict) -> list[str]:
    """Avisos (nunca errores) de valores fuera del rango declarado.

    No modifica `data` ni impide cargarlo: un valor fuera de rango puede ser
    una decision deliberada de calidad, no un dato corrupto.
    """
    avisos: list[str] = []
    for seccion, campo in iter_fields():
        valor = data.get(seccion.key, {}).get(campo.key)
        if valor is None or campo.kind == "bool":
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
