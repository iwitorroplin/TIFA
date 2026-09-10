"""Selector de programa: buscador + lista corta, o consigna a mano.

Sustituye al QComboBox que usaban la pestaña de Ciclos y la ventana de
detalle. Con ~50 programas (ver `tools/seed_ferlo_programs.py`) un desplegable
obliga a recorrer la lista entera a ojo, y varios comparten nombre y solo se
distinguen por el tiempo -ver los códigos 20/31 y 25/41-.

Dos modos excluyentes, que es la razón de que esto sea un widget y no dos
sueltos: o se elige un programa de la lista, o se teclea la consigna a mano.
Un `QRadioButton` decide cuál manda, para que no quede nunca ambiguo cuál de
los dos se va a aplicar al pulsar Asignar.

El modo manual NO crea ni edita un programa de `ferlo_program`: la consigna
viaja con el ciclo. Ver `logic/analysis/programs.py:manual_program`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.analysis.models import SterilizationProgram
from src.modules.ferlo.logic.analysis.programs import MANUAL_PROGRAM_CODE, ManualSetpoint

# Centinela de "— sin asignar —", que no es ningún código de programa. Es el
# mismo papel que juega UNASSIGNED_PROGRAM en data_presenter.py, pero como
# dato de una fila de la lista.
UNASSIGNED = object()

# Filas visibles sin desplazar. Diez es lo que pidió la planta: entran los
# sugeridos y unos cuantos más sin que la lista se coma la ventana.
_VISIBLE_ROWS = 10


class ProgramSelector(QWidget):
    """Elige programa de la lista o consigna manual.

    `selection_changed` se emite en cada cambio para que quien lo use pueda
    habilitar o deshabilitar su botón de Asignar: la selección puede quedar
    inválida (modo manual con temperatura a 0, o ninguna fila elegida).
    """

    selection_changed = Signal()

    def __init__(
        self,
        programs: list[SterilizationProgram],
        *,
        suggested: list[SterilizationProgram] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # El programa 0 es la fila centinela de la consigna manual (ver
        # `logic/schema.py`), no una posición del autoclave: nunca se ofrece
        # como opción elegible -para eso está el modo manual-.
        self._programs = [p for p in programs if p.code != MANUAL_PROGRAM_CODE]
        self._suggested = suggested or []
        self._build_ui()
        self._populate()

    # -- construcción ----------------------------------------------------

    def _build_ui(self) -> None:
        self._from_list_radio = QRadioButton("Elegir de la lista")
        self._from_list_radio.setChecked(True)
        self._from_list_radio.toggled.connect(self._on_mode_changed)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Buscar por código, nombre o formato...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._apply_filter)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.currentItemChanged.connect(lambda *_: self.selection_changed.emit())
        self._list.setAlternatingRowColors(True)

        self._manual_radio = QRadioButton("Consigna a mano")
        self._manual_radio.toggled.connect(self._on_mode_changed)

        # Rangos amplios a propósito: son los de la planta (105-130 °C, 9-90
        # min en los programas actuales) con holgura, no una validación de
        # proceso -quien teclea sabe lo que hace-.
        self._temperature_spin = QDoubleSpinBox()
        self._temperature_spin.setRange(0.0, 200.0)
        self._temperature_spin.setDecimals(1)
        self._temperature_spin.setSingleStep(0.5)
        self._temperature_spin.setSuffix(" °C")
        self._temperature_spin.valueChanged.connect(lambda *_: self.selection_changed.emit())

        self._time_spin = QDoubleSpinBox()
        self._time_spin.setRange(0.0, 600.0)
        self._time_spin.setDecimals(1)
        self._time_spin.setSingleStep(1.0)
        self._time_spin.setSuffix(" min")
        self._time_spin.valueChanged.connect(lambda *_: self.selection_changed.emit())

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel("Temperatura:"))
        manual_row.addWidget(self._temperature_spin)
        manual_row.addSpacing(12)
        manual_row.addWidget(QLabel("Tiempo:"))
        manual_row.addWidget(self._time_spin)
        manual_row.addStretch()

        self._manual_row_widget = QWidget()
        self._manual_row_widget.setLayout(manual_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._from_list_radio)
        layout.addWidget(self._search_edit)
        layout.addWidget(self._list)
        layout.addWidget(self._manual_radio)
        layout.addWidget(self._manual_row_widget)

        self._on_mode_changed()

    def _populate(self) -> None:
        self._list.clear()
        self._add_row("— sin asignar —", UNASSIGNED, searchable="sin asignar")

        codigos_sugeridos = {p.code for p in self._suggested}
        for programa in self._suggested:
            self._add_program(programa, suggested=True)
        for programa in self._programs:
            if programa.code not in codigos_sugeridos:
                self._add_program(programa, suggested=False)

        self._list.setCurrentRow(0)
        self._apply_height()

    def _add_program(self, programa: SterilizationProgram, *, suggested: bool) -> None:
        etiqueta = f"{programa.display_code} · {programa.display_name}"
        if programa.name:
            etiqueta = f"{programa.display_code} · {programa.name} · {programa.display_name}"
        if programa.format:
            etiqueta += f" · {programa.format}"
        if not programa.is_active:
            etiqueta += " (inactivo)"
        if suggested:
            etiqueta = f"★ {etiqueta}"
        # El texto buscable incluye nombre y formato aunque la etiqueta los
        # recorte: buscar "1/2" tiene que encontrar los de medio kilo.
        buscable = f"{programa.code:02d} {programa.name} {programa.format} {programa.display_name}"
        self._add_row(etiqueta, programa.code, searchable=buscable)

    def _add_row(self, label: str, data: object, *, searchable: str) -> None:
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, data)
        # El filtro compara siempre en minúsculas contra este texto, no
        # contra la etiqueta: así el ★ y el "(inactivo)" no interfieren.
        item.setData(Qt.ItemDataRole.UserRole + 1, searchable.lower())
        self._list.addItem(item)

    def _apply_height(self) -> None:
        """Fija la altura a `_VISIBLE_ROWS` filas: el resto se ve desplazando.

        Con altura libre, un QListWidget dentro de un layout vertical crece
        hasta ocupar lo que le dejen -50 programas estirarían la ventana de
        detalle fuera de la pantalla-.
        """
        fila = self._list.sizeHintForRow(0)
        if fila <= 0:
            fila = self.fontMetrics().height() + 6
        marco = 2 * self._list.frameWidth()
        self._list.setFixedHeight(fila * _VISIBLE_ROWS + marco)

    # -- comportamiento --------------------------------------------------

    def _on_mode_changed(self) -> None:
        de_lista = self._from_list_radio.isChecked()
        self._search_edit.setEnabled(de_lista)
        self._list.setEnabled(de_lista)
        self._manual_row_widget.setEnabled(not de_lista)
        self.selection_changed.emit()

    def _apply_filter(self, texto: str) -> None:
        aguja = texto.strip().lower()
        for fila in range(self._list.count()):
            item = self._list.item(fila)
            buscable = item.data(Qt.ItemDataRole.UserRole + 1) or ""
            item.setHidden(bool(aguja) and aguja not in buscable)

        # Si el filtro esconde la fila elegida, la selección dejaría de verse
        # pero seguiría contando al pulsar Asignar: se mueve a la primera
        # visible para que lo que se aplica sea siempre lo que se está viendo.
        actual = self._list.currentItem()
        if actual is not None and not actual.isHidden():
            return
        for fila in range(self._list.count()):
            if not self._list.item(fila).isHidden():
                self._list.setCurrentRow(fila)
                return
        self._list.setCurrentRow(-1)

    # -- lectura del resultado -------------------------------------------

    @property
    def is_manual(self) -> bool:
        return self._manual_radio.isChecked()

    def manual_setpoint(self) -> ManualSetpoint | None:
        """Consigna tecleada, o None si no está en modo manual o está a 0."""
        if not self.is_manual:
            return None
        temperatura = self._temperature_spin.value()
        tiempo = self._time_spin.value()
        if temperatura <= 0 or tiempo <= 0:
            return None
        return ManualSetpoint(target_temperature_c=temperatura, target_time_min=tiempo)

    def program_code(self) -> int | None:
        """Código elegido, o None para "sin asignar". Solo en modo lista."""
        item = self._list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return None if data is UNASSIGNED else int(data)

    def has_valid_selection(self) -> bool:
        """Si hay algo aplicable. En manual exige temperatura y tiempo > 0;
        en lista, que haya una fila elegida -el filtro puede dejarla vacía-."""
        if self.is_manual:
            return self.manual_setpoint() is not None
        return self._list.currentItem() is not None

    # -- estado inicial ---------------------------------------------------

    def select_program(self, code: int | None) -> None:
        """Deja preseleccionado el programa de un ciclo ya asignado."""
        if code == MANUAL_PROGRAM_CODE:
            # Ciclo con consigna manual: no hay fila que seleccionar, la
            # consigna vive en el propio ciclo. Quien llama rellena los spin
            # con `set_manual_setpoint`.
            self._manual_radio.setChecked(True)
            return
        objetivo = UNASSIGNED if code is None else code
        for fila in range(self._list.count()):
            if self._list.item(fila).data(Qt.ItemDataRole.UserRole) == objetivo:
                self._list.setCurrentRow(fila)
                return

    def set_manual_setpoint(self, target_temperature_c: float, target_time_min: float) -> None:
        self._temperature_spin.setValue(target_temperature_c)
        self._time_spin.setValue(target_time_min)
