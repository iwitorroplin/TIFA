from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox, QSizePolicy, QSpinBox, QWidget

from src.modules.ferlo.logic.config import SETTINGS_SCHEMA

# Varios grupos por fila, en vez de una sola columna: con tantas secciones,
# apilarlas todas verticalmente desperdiciaba ancho de página.
_SECTIONS_PER_ROW = 3

# Estas 4 secciones se editan en el modal de ejemplo visual
# (`CycleVariablesDialog`), donde se ven sobre la curva de un ciclo en vez de
# como spinboxes sueltos. `sampling` se queda aquí: es un intervalo de
# muestreo, no algo que tenga sentido dibujar sobre esa curva.
_SECTIONS_IN_DIALOG = {"cycle_detection", "sterilization_phase", "acceptance", "review"}
_GRID_SECTIONS = tuple(s for s in SETTINGS_SCHEMA if s.key not in _SECTIONS_IN_DIALOG)


class SectionsGrid(QGridLayout):
    """Rejilla de secciones generada desde `SETTINGS_SCHEMA`
    (`logic/config.py`): añadir un umbral nuevo no toca este fichero."""

    def __init__(self, draft: dict, on_change, parent: QWidget | None = None):
        super().__init__(parent)
        self._draft = draft
        self._on_change = on_change
        self._spinboxes: dict[tuple[str, str], QWidget] = {}

        for col in range(_SECTIONS_PER_ROW):
            self.setColumnStretch(col, 1)
        for index, section in enumerate(_GRID_SECTIONS):
            row, col = divmod(index, _SECTIONS_PER_ROW)
            group = self._build_section_group(section)
            group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.addWidget(group, row, col, alignment=Qt.AlignmentFlag.AlignTop)

    def _build_section_group(self, section):
        group = QGroupBox(section.label)
        form = QFormLayout(group)
        for field in section.fields:
            spin = self._build_field_spinbox(section, field)
            self._spinboxes[(section.key, field.key)] = spin
            label = f"{field.label} ({field.unit})" if field.unit else field.label
            form.addRow(label, spin)
            if field.help:
                spin.setToolTip(field.help)
        return group

    def _build_field_spinbox(self, section, field):
        valor = self._draft[section.key][field.key]
        if field.kind == "int":
            spin = QSpinBox()
            minimo = 0 if field.minimum is None else int(field.minimum)
            maximo = 0 if field.maximum is None else int(field.maximum)
            spin.setRange(minimo, maximo)
            spin.setValue(int(valor))
        else:
            spin = QDoubleSpinBox()
            spin.setDecimals(field.decimals)
            spin.setRange(
                field.minimum if field.minimum is not None else -1e9,
                field.maximum if field.maximum is not None else 1e9,
            )
            spin.setSingleStep(10 ** (-field.decimals) if field.decimals else 1.0)
            spin.setValue(float(valor))
        # La unidad la lleva ya la etiqueta de la fila (`_build_section_group`):
        # ponerla además como sufijo del campo la mostraba dos veces y dejaba
        # el cursor detrás del texto al escribir.
        spin.valueChanged.connect(lambda value, s=section, f=field: self._on_field_changed(s, f, value))
        return spin

    def _on_field_changed(self, section, field, value):
        self._draft[section.key][field.key] = value
        self._on_change()

    def repaint(self):
        for (section_key, field_key), spin in self._spinboxes.items():
            spin.blockSignals(True)
            spin.setValue(self._draft[section_key][field_key])
            spin.blockSignals(False)
