"""Modal de ejemplo visual para las variables de deteccion de ciclos.

Unico sitio donde se editan las secciones `cycle_detection`,
`sterilization_phase`, `acceptance` y `review` de `SETTINGS_SCHEMA`
(`sampling` se queda en `SectionsGrid`: es un intervalo de muestreo, no algo
que tenga sentido dibujar sobre la curva de un ciclo). Edita el mismo draft
que `FerloConfigPage`, así que "Guardar" en la página persiste tambien lo que
se cambie aquí -no es un ejemplo desechable como las 2 variables iniciales,
ver `diagrama_ejemplo_var.md`.

`temp_dummy`/`tiempo_dummy` son la consigna de ejemplo sobre la que se
dibujan las variables relativas (bandas de tolerancia, ventanas de tiempo);
son puramente esteticas -no se guardan, cada apertura del modal parte de los
mismos valores por defecto (110 °C / 30 min).

Cada variable se dibuja segun su significado real en `logic/analysis/`, no
solo por su unidad -dos campos en °C pueden significar cosas geometricamente
distintas (un umbral absoluto no es lo mismo que una banda bajo consigna):

- Umbrales absolutos de temperatura (`cycle_start_temperature_c`,
  `cycle_end_temperature_c`, `min_cycle_peak_temperature_c`,
  `setpoint_mode_floor_c`): linea horizontal en su propio valor.
- Bandas relativas a consigna (`sterilization_tolerance_c`,
  `acceptance_tolerance_c`): linea horizontal en `temp_dummy - valor`
  (ver phases.py y validate.py: la banda/minimo admisible se calculan
  restando de la consigna).
- Desviacion simetrica (`review_deviation_c`): dos lineas horizontales, en
  `temp_dummy - valor` y `temp_dummy + valor` (validate.py compara
  `abs(desviacion)`, no tiene signo).
- `setpoint_mode_bin_c` es una resolucion de redondeo, no un umbral: no se
  dibuja, solo queda como spinbox editable.
- Duracion minima del ciclo (`min_cycle_duration_min`): marca vertical desde
  el inicio real del ciclo (x=0).
- Ventana de estabilizacion (`stabilization_window_min`): tramo vertical
  desde el INICIO de la meseta (asi se excluye de las medias, ver
  metrics.py).
- Antirrebote de salida (`exit_debounce_s`) y tolerancia de tiempo de
  aceptacion (`acceptance_time_tolerance_min`): tramo vertical antes del
  FINAL de la meseta (la salida de fase y el minimo admisible de duracion
  ocurren ahi, ver phases.py/validate.py). La posicion se acota (clamp) al
  tramo de la meseta: con `tiempo_dummy` pequeño y el campo en su maximo, la
  resta podia caer antes del inicio de la meseta o fuera de la curva.

`exit_debounce_s` se guarda en segundos (asi lo usan phases.py/validate.py:
no se toca su unidad real, ver decision tomada) pero aqui se edita en
minutos -es la unica variable de tiempo del grupo que no estaba ya en
minutos, y mezclada con las demas confundia mas que ayudaba.

Por defecto todas discontinuas y finas; la que tiene el foco pasa a linea
continua, mas gruesa y en otro color. Cada variable tiene su checkbox de
"visible en la grafica" (con un maestro que marca/desmarca todas) y un
botón "?" que despliega una breve ayuda encima del campo -sin popup modal.
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.config import SETTINGS_SCHEMA
from src.shared.ui.components.app_button import AppButton

# Solo estas 4 secciones se editan aquí; `sampling` se queda en SectionsGrid.
_DIALOG_SECTION_KEYS = ("cycle_detection", "sterilization_phase", "acceptance", "review")
_DIALOG_SECTIONS = tuple(s for s in SETTINGS_SCHEMA if s.key in _DIALOG_SECTION_KEYS)

# Unico campo que se edita en una unidad distinta a la guardada: ver
# docstring del modulo. (seccion, campo) -> factor de conversion a la unidad
# guardada (guardado = mostrado * factor).
_MINUTES_TO_SECONDS_FIELDS = {("sterilization_phase", "exit_debounce_s")}

_TEMP_DUMMY_DEFAULT_C = 110.0
_TIME_DUMMY_DEFAULT_MIN = 30.0
_TEMP_DUMMY_RANGE = (0.0, 150.0)
_TIME_DUMMY_RANGE = (1.0, 300.0)

_COLOR_IDLE = "#4d88cb"
_COLOR_SELECTED = "#e2790c"
_COLOR_DUMMY = "#3fa34d"
_PEN_IDLE_WIDTH = 1
_PEN_SELECTED_WIDTH = 3

# Rampas de subida/bajada fijas, solo para dar forma de ciclo a la curva de
# ejemplo -la meseta escala con tiempo_dummy para que las variables de tiempo
# siempre caigan dentro del tramo dibujado.
_CURVE_BASELINE_C = 20.0
_CURVE_RAMP_MIN = 10.0


# key de campo -> como se dibuja sobre la curva. Cada entrada es una funcion
# `(value, temp_dummy, meseta_inicio, meseta_fin) -> list[(orientacion, posicion)]`,
# con orientacion "h" (horizontal, en temperatura) o "v" (vertical, en tiempo).
def _abs_temp(value, temp_dummy, meseta_inicio, meseta_fin):
    return [("h", value)]


def _band_below(value, temp_dummy, meseta_inicio, meseta_fin):
    return [("h", temp_dummy - value)]


def _symmetric_band(value, temp_dummy, meseta_inicio, meseta_fin):
    return [("h", temp_dummy - value), ("h", temp_dummy + value)]


def _from_cycle_start(value, temp_dummy, meseta_inicio, meseta_fin):
    return [("v", value)]


def _from_plateau_start(value, temp_dummy, meseta_inicio, meseta_fin):
    return [("v", meseta_inicio + value)]


def _before_plateau_end(value, temp_dummy, meseta_inicio, meseta_fin):
    # Acotado al tramo de la meseta: un valor grande con tiempo_dummy pequeño
    # puede restar mas de lo que dura la meseta -sin el clamp, la linea caia
    # antes de meseta_inicio o del todo fuera de la curva dibujada.
    posicion = max(meseta_inicio, min(meseta_fin, meseta_fin - value))
    return [("v", posicion)]


_FIELD_GEOMETRY = {
    ("cycle_detection", "cycle_start_temperature_c"): _abs_temp,
    ("cycle_detection", "cycle_end_temperature_c"): _abs_temp,
    ("cycle_detection", "min_cycle_peak_temperature_c"): _abs_temp,
    ("cycle_detection", "setpoint_mode_floor_c"): _abs_temp,
    ("cycle_detection", "min_cycle_duration_min"): _from_cycle_start,
    # setpoint_mode_bin_c: resolucion de redondeo, sin geometria -no aparece aquí.
    ("sterilization_phase", "sterilization_tolerance_c"): _band_below,
    ("sterilization_phase", "exit_debounce_s"): _before_plateau_end,
    ("sterilization_phase", "stabilization_window_min"): _from_plateau_start,
    ("acceptance", "acceptance_tolerance_c"): _band_below,
    ("acceptance", "acceptance_time_tolerance_min"): _before_plateau_end,
    ("review", "review_deviation_c"): _symmetric_band,
}


class CycleVariablesDialog(QDialog):
    def __init__(self, draft: dict, on_change, parent: QWidget | None = None):
        super().__init__(parent)
        self._draft = draft
        self._on_change = on_change
        self._selected_key: tuple[str, str] | None = None
        # (section_key, field_key) -> spinbox
        self._spinboxes: dict[tuple[str, str], QWidget] = {}
        # (section_key, field_key) -> checkbox de "visible en la grafica"
        self._visibility_checkboxes: dict[tuple[str, str], QCheckBox] = {}

        self.setWindowTitle("Variables de deteccion de ciclo")
        self.resize(1280, 640)

        self._temp_dummy_spin = self._build_dummy_spin(
            _TEMP_DUMMY_DEFAULT_C, _TEMP_DUMMY_RANGE, " °C", 1
        )
        self._time_dummy_spin = self._build_dummy_spin(
            _TIME_DUMMY_DEFAULT_MIN, _TIME_DUMMY_RANGE, " min", 1
        )

        self._plot = pg.PlotWidget()
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.setLabel("bottom", "Tiempo", units="min")
        self._plot.setLabel("left", "Temperatura", units="°C")

        columns = QHBoxLayout()
        columns.addWidget(self._build_fields_panel(), 0)
        columns.addWidget(self._plot, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_hint())
        layout.addWidget(self._build_dummy_group())
        layout.addWidget(self._build_visibility_master_row())
        layout.addLayout(columns, 1)
        layout.addLayout(self._build_bottom_bar())

        self._redraw()

    def _build_hint(self) -> QWidget:
        label = QLabel(
            "Selecciona una variable (clic en su campo) para verla resaltada en la "
            "curva. Los cambios de la lista se guardan igual que el resto de la "
            "configuración, con el botón \"Guardar\" de la página."
        )
        label.setWordWrap(True)
        return label

    # --- consigna de ejemplo: puramente estetica, no se guarda ---

    def _build_dummy_spin(self, default: float, value_range: tuple[float, float], suffix: str, decimals: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(*value_range)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        spin.setValue(default)
        spin.valueChanged.connect(self._redraw)
        return spin

    def _build_dummy_group(self) -> QWidget:
        group = QGroupBox("Consigna de ejemplo (no se guarda)")
        form = QFormLayout(group)
        form.addRow("Temperatura de consigna:", self._temp_dummy_spin)
        form.addRow("Tiempo de consigna:", self._time_dummy_spin)
        return group

    # --- fila maestra: mostrar todas / ninguna ---

    def _build_visibility_master_row(self) -> QWidget:
        self._master_checkbox = QCheckBox("Mostrar todas las variables en la gráfica")
        self._master_checkbox.setChecked(True)
        self._master_checkbox.setTristate(True)
        self._master_checkbox.clicked.connect(self._on_master_visibility_clicked)
        return self._master_checkbox

    def _on_master_visibility_clicked(self) -> None:
        # clicked (no stateChanged): con tristate, un clic del usuario nunca
        # debe aterrizar en "parcial" -eso solo lo pone _sync_master_checkbox
        # al reflejar el estado de las variables sueltas.
        mostrar = self._master_checkbox.checkState() != Qt.CheckState.Unchecked
        self._master_checkbox.blockSignals(True)
        self._master_checkbox.setCheckState(
            Qt.CheckState.Checked if mostrar else Qt.CheckState.Unchecked
        )
        self._master_checkbox.blockSignals(False)

        for checkbox in self._visibility_checkboxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(mostrar)
            checkbox.blockSignals(False)
        self._redraw()

    def _sync_master_checkbox(self) -> None:
        estados = {cb.isChecked() for cb in self._visibility_checkboxes.values()}
        self._master_checkbox.blockSignals(True)
        if estados == {True}:
            self._master_checkbox.setCheckState(Qt.CheckState.Checked)
        elif estados == {False}:
            self._master_checkbox.setCheckState(Qt.CheckState.Unchecked)
        else:
            self._master_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self._master_checkbox.blockSignals(False)

    # --- panel izquierdo: los grupos de sección repartidos en 2 columnas
    # (SETTINGS_SCHEMA, como SectionsGrid) -con las 4 secciones en una sola
    # columna la lista de 12 variables quedaba demasiado larga ---

    _SECTIONS_PER_ROW = 2

    def _build_fields_panel(self) -> QWidget:
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        for col in range(self._SECTIONS_PER_ROW):
            grid.setColumnStretch(col, 1)
        for index, section in enumerate(_DIALOG_SECTIONS):
            row, col = divmod(index, self._SECTIONS_PER_ROW)
            group = self._build_section_group(section)
            grid.addWidget(group, row, col, alignment=Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setMinimumWidth(520)
        scroll.setMaximumWidth(600)
        scroll.setWidget(content)
        return scroll

    def _build_section_group(self, section) -> QWidget:
        group = QGroupBox(section.label)
        layout = QVBoxLayout(group)
        for field in section.fields:
            layout.addWidget(self._build_field_row(section, field))
        return group

    def _build_field_row(self, section, field) -> QWidget:
        key = (section.key, field.key)

        spin = self._build_field_spinbox(section, field)
        self._spinboxes[key] = spin
        if field.help:
            spin.setToolTip(field.help)

        # La unidad del label sigue la que se muestra en el spinbox, no la
        # guardada: exit_debounce_s se edita en min aunque se guarde en s.
        unidad_mostrada = "min" if key in _MINUTES_TO_SECONDS_FIELDS else field.unit
        label_text = f"{field.label} ({unidad_mostrada})" if unidad_mostrada else field.label
        label = QLabel(label_text)
        if field.help:
            label.setToolTip(field.help)

        visibility_checkbox = QCheckBox()
        visibility_checkbox.setChecked(True)
        visibility_checkbox.setToolTip("Ver esta variable en la gráfica")
        if (section.key, field.key) not in _FIELD_GEOMETRY:
            visibility_checkbox.setEnabled(False)
        else:
            visibility_checkbox.stateChanged.connect(lambda _: self._on_visibility_changed())
        self._visibility_checkboxes[key] = visibility_checkbox

        field_row = QHBoxLayout()
        field_row.setContentsMargins(0, 0, 0, 0)
        field_row.addWidget(visibility_checkbox)
        field_row.addWidget(spin, 1)

        wrapper = QWidget()
        column = QVBoxLayout(wrapper)
        column.setContentsMargins(0, 4, 0, 4)
        column.addWidget(label)
        column.addLayout(field_row)
        return wrapper

    def _on_visibility_changed(self) -> None:
        self._sync_master_checkbox()
        self._redraw()

    def _build_field_spinbox(self, section, field):
        raw_value = self._draft[section.key][field.key]
        shown_in_minutes = (section.key, field.key) in _MINUTES_TO_SECONDS_FIELDS

        if shown_in_minutes:
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            minimo = 0.0 if field.minimum is None else field.minimum / 60.0
            maximo = 0.0 if field.maximum is None else field.maximum / 60.0
            spin.setRange(minimo, maximo)
            spin.setSuffix(" min")
            spin.setValue(float(raw_value) / 60.0)
        elif field.kind == "int":
            spin = QSpinBox()
            minimo = 0 if field.minimum is None else int(field.minimum)
            maximo = 0 if field.maximum is None else int(field.maximum)
            spin.setRange(minimo, maximo)
            spin.setValue(int(raw_value))
        else:
            spin = QDoubleSpinBox()
            spin.setDecimals(field.decimals)
            spin.setRange(
                field.minimum if field.minimum is not None else -1e9,
                field.maximum if field.maximum is not None else 1e9,
            )
            spin.setSingleStep(10 ** (-field.decimals) if field.decimals else 1.0)
            spin.setValue(float(raw_value))

        spin.valueChanged.connect(
            lambda value, s=section, f=field, m=shown_in_minutes: self._on_field_changed(s, f, value, m)
        )
        spin.installEventFilter(self)
        return spin

    def _on_field_changed(self, section, field, value, shown_in_minutes: bool) -> None:
        self._draft[section.key][field.key] = round(value * 60.0) if shown_in_minutes else value
        self._on_change()
        self._redraw()

    def eventFilter(self, watched, event):
        # Seleccionar la variable resaltada por foco del spinbox: no hay lista
        # aparte que sincronizar, el usuario "selecciona" la variable al
        # tocarla, igual que en la primera versión de este modal.
        if event.type() == QEvent.Type.FocusIn:
            for key, spin in self._spinboxes.items():
                if watched is spin and key != self._selected_key:
                    self._selected_key = key
                    self._redraw()
                    break
        return super().eventFilter(watched, event)

    def _build_bottom_bar(self) -> QHBoxLayout:
        close_button = AppButton("Cerrar")
        close_button.clicked.connect(self.close)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_button)
        return row

    # --- grafica: curva de fondo + una linea por variable visible ---

    def _redraw(self) -> None:
        self._plot.clear()

        temp_dummy = self._temp_dummy_spin.value()
        tiempo_dummy = self._time_dummy_spin.value()
        meseta_inicio = _CURVE_RAMP_MIN
        meseta_fin = _CURVE_RAMP_MIN + tiempo_dummy

        xs, ys = self._build_curve(temp_dummy, meseta_inicio, meseta_fin)
        self._plot.plot(xs, ys, pen=pg.mkPen("#3a3a3a", width=2))

        self._plot.addLine(
            y=temp_dummy, pen=pg.mkPen(_COLOR_DUMMY, width=1, style=Qt.PenStyle.DashDotLine)
        )
        self._plot.addLine(
            x=meseta_inicio, pen=pg.mkPen(_COLOR_DUMMY, width=1, style=Qt.PenStyle.DashDotLine)
        )
        self._plot.addLine(
            x=meseta_fin, pen=pg.mkPen(_COLOR_DUMMY, width=1, style=Qt.PenStyle.DashDotLine)
        )

        for section in _DIALOG_SECTIONS:
            for field in section.fields:
                self._draw_field_line(section, field, temp_dummy, meseta_inicio, meseta_fin)

    def _draw_field_line(self, section, field, temp_dummy, meseta_inicio, meseta_fin) -> None:
        key = (section.key, field.key)
        geometry = _FIELD_GEOMETRY.get(key)
        if geometry is None:
            return
        checkbox = self._visibility_checkboxes.get(key)
        if checkbox is not None and not checkbox.isChecked():
            return

        value = self._draft[section.key][field.key]
        selected = key == self._selected_key

        color = _COLOR_SELECTED if selected else _COLOR_IDLE
        width = _PEN_SELECTED_WIDTH if selected else _PEN_IDLE_WIDTH
        style = Qt.PenStyle.SolidLine if selected else Qt.PenStyle.DashLine
        pen = pg.mkPen(color, width=width, style=style)
        label = f"{field.label} ({value:g} {field.unit})" if field.unit else f"{field.label} ({value:g})"

        posiciones = geometry(value, temp_dummy, meseta_inicio, meseta_fin)
        for index, (orientacion, posicion) in enumerate(posiciones):
            mostrar_label = selected and index == 0
            if orientacion == "h":
                self._plot.addLine(y=posicion, pen=pen, label=label if mostrar_label else None)
            else:
                self._plot.addLine(x=posicion, pen=pen, label=label if mostrar_label else None)

    def _build_curve(self, temp_dummy, meseta_inicio, meseta_fin) -> tuple[list[float], list[float]]:
        # Curva puramente ilustrativa (subida-meseta-bajada), no una
        # simulacion fisica ni un ciclo real: solo da contexto visual a las
        # lineas de las variables. La meseta escala con tiempo_dummy para que
        # las variables de tiempo caigan siempre dentro del tramo dibujado.
        fin = meseta_fin + _CURVE_RAMP_MIN

        xs = [0.0, meseta_inicio, meseta_fin, fin]
        ys = [_CURVE_BASELINE_C, temp_dummy, temp_dummy, _CURVE_BASELINE_C]
        return xs, ys
