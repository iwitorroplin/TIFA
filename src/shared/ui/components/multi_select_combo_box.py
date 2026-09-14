"""Combo desplegable de selección múltiple con checkboxes.

Sustituye tanto al `QComboBox` de selección única (Ferlo, filtro de máquina)
como a la fila de un `QCheckBox` por autoclave (Steriflow, filtro de
autoclave): mismo filtro, un solo widget reutilizable en los dos módulos en
vez de dos formas distintas de resolver lo mismo.

No conoce nada del dominio -ni autoclaves, ni máquinas, ni programas-: solo
pares (texto, valor) y qué filas están marcadas. Quien lo usa decide qué es
`value` y qué hace con `selected_values()` (p. ej. convertir "todo marcado"
en "sin filtrar" es cosa de cada `FiltersRow`, no de este widget).
"""

from __future__ import annotations

from typing import Hashable, Iterable

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox, QStylePainter

# Centinela para "no se ha pasado valor": permite que `None` sea, si alguien
# lo quiere así, un valor real de un ítem (p. ej. un "sin asignar"), en vez
# de estar reservado para "usa el texto como valor".
_USE_TEXT_AS_VALUE = object()

# Hueco aproximado que Qt reserva para la flecha del desplegable: sin restar
# esto, `_display_text` cabría "de más" y el texto se comería la flecha.
_ARROW_WIDTH_PX = 30

# Ancho mínimo por defecto. Sin esto, en una fila con varios filtros y un
# `addStretch()` al final (ver `FiltersRow` de Ferlo y Steriflow) el layout
# puede dejarle al combo casi cero espacio, y el resumen de la selección
# ("AUTOCLAVE6, AUTOCLAVE7...") queda cortado o no se ve.
_DEFAULT_MIN_WIDTH_PX = 160


class MultiSelectComboBox(QComboBox):
    """QComboBox donde cada fila lleva un checkbox y se puede marcar más de
    una sin que el desplegable se cierre en el primer clic.

    El texto mostrado resume la selección: "Todas" si están todas marcadas,
    "Ninguna" si no hay ninguna, la lista separada por comas si cabe
    ("F1, F3"), o "N de M" cuando no cabe. El tooltip siempre lleva la lista
    completa.

    `selection_changed` se emite una sola vez por cada cambio real de la
    selección -también tras `select_all()`/`set_selected_values()`-, nunca
    una vez por fila tocada internamente.

    Es una subclase de `QComboBox` y no una composición: encaja directamente
    en cualquier layout con el mismo tamaño y estilo que los demás combos de
    la pantalla. La contrapartida es que sigue teniendo métodos heredados
    como `addItem`/`setCurrentIndex`/`currentText` que NO pasan por el
    control de las marcas -no usarlos aquí; para eso están `add_item` y
    compañía-.
    """

    selection_changed = Signal()

    def __init__(
        self,
        parent=None,
        *,
        all_text: str = "Todas",
        none_text: str = "Ninguna",
        show_select_all_row: bool = True,
        min_width: int = _DEFAULT_MIN_WIDTH_PX,
    ) -> None:
        super().__init__(parent)
        self._all_text = all_text
        self._none_text = none_text
        self._show_select_all_row = show_select_all_row
        self.setMinimumWidth(min_width)
        self._select_all_item: QStandardItem | None = None
        # Evita que `_on_item_changed` reaccione a la marca de la propia fila
        # "Todas" cuando es `_sync_select_all_row` quien la está recalculando
        # -si no, ese recálculo se interpretaría como un clic del usuario y
        # dispararía `_set_all` en bucle.
        self._updating_select_all = False
        self._previous_selection: tuple[Hashable, ...] = ()

        self._item_model = QStandardItemModel(self)
        self.setModel(self._item_model)
        self._item_model.itemChanged.connect(self._on_item_changed)

        if show_select_all_row:
            self._select_all_item = self._new_item(all_text, checked=False)
            self._item_model.appendRow(self._select_all_item)

        # Los clics normales sobre una fila del desplegable hacen que
        # QComboBox la seleccione y cierre el popup -justo lo que no
        # queremos con varias marcas a la vez-. Se interceptan aquí, antes
        # de que le lleguen a la vista.
        self.view().installEventFilter(self)
        self.view().viewport().installEventFilter(self)

    # -- contenido ---------------------------------------------------

    def add_item(self, text: str, value: Hashable = _USE_TEXT_AS_VALUE, *, checked: bool = False) -> None:
        if value is _USE_TEXT_AS_VALUE:
            value = text
        if value in self._value_to_item():
            raise ValueError(f"valor repetido en MultiSelectComboBox: {value!r}")
        item = self._new_item(text, checked=checked)
        item.setData(value, Qt.ItemDataRole.UserRole)
        self._item_model.appendRow(item)
        self._sync_select_all_row()
        self._refresh_display()

    def add_items(self, items: Iterable[tuple[str, Hashable]], *, checked: bool = False) -> None:
        for text, value in items:
            self.add_item(text, value, checked=checked)

    def remove_item(self, value: Hashable) -> None:
        item = self._value_to_item().get(value)
        if item is None:
            return
        self._item_model.removeRow(item.row())
        self._sync_select_all_row()
        self._refresh_display()

    def clear_items(self) -> None:
        self._item_model.removeRows(0, self._item_model.rowCount())
        if self._show_select_all_row:
            self._select_all_item = self._new_item(self._all_text, checked=False)
            self._item_model.appendRow(self._select_all_item)
        self._refresh_display()

    # -- selección -----------------------------------------------------

    def selected_values(self) -> list[Hashable]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self._data_items() if self._is_checked(item)]

    def selected_texts(self) -> list[str]:
        return [item.text() for item in self._data_items() if self._is_checked(item)]

    def set_selected_values(self, values: Iterable[Hashable]) -> None:
        deseados = set(values)
        self._item_model.blockSignals(True)
        try:
            for item in self._data_items():
                self._set_checked(item, item.data(Qt.ItemDataRole.UserRole) in deseados)
        finally:
            self._item_model.blockSignals(False)
        self._sync_select_all_row()
        self._refresh_display()
        self._notify_if_changed()

    def select_all(self) -> None:
        self._set_all(checked=True)

    def deselect_all(self) -> None:
        self._set_all(checked=False)

    def is_all_selected(self) -> bool:
        items = self._data_items()
        return bool(items) and all(self._is_checked(item) for item in items)

    # -- construcción de ítems -----------------------------------------

    @staticmethod
    def _new_item(text: str, *, checked: bool) -> QStandardItem:
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        return item

    @staticmethod
    def _is_checked(item: QStandardItem) -> bool:
        return item.checkState() == Qt.CheckState.Checked

    @staticmethod
    def _set_checked(item: QStandardItem, checked: bool) -> None:
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def _data_items(self) -> list[QStandardItem]:
        primera_fila = 1 if self._show_select_all_row else 0
        return [self._item_model.item(fila) for fila in range(primera_fila, self._item_model.rowCount())]

    def _value_to_item(self) -> dict[Hashable, QStandardItem]:
        return {item.data(Qt.ItemDataRole.UserRole): item for item in self._data_items()}

    # -- eventos: marcar sin cerrar el desplegable -----------------------

    def eventFilter(self, watched, event) -> bool:
        if watched is self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.position().toPoint())
            if index.isValid():
                self._toggle_row(index.row())
                return True
        if watched is self.view() and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                index = self.view().currentIndex()
                if index.isValid():
                    self._toggle_row(index.row())
                    return True
        return super().eventFilter(watched, event)

    def _toggle_row(self, row: int) -> None:
        item = self._item_model.item(row)
        if item is None:
            return
        self._set_checked(item, not self._is_checked(item))

    # -- reacción a marcas individuales -----------------------------------

    def _on_item_changed(self, item: QStandardItem) -> None:
        if item is self._select_all_item:
            if self._updating_select_all:
                return
            self._set_all(checked=self._is_checked(item))
            return
        self._sync_select_all_row()
        self._refresh_display()
        self._notify_if_changed()

    def _set_all(self, *, checked: bool) -> None:
        self._item_model.blockSignals(True)
        try:
            for item in self._data_items():
                self._set_checked(item, checked)
            if self._select_all_item is not None:
                self._set_checked(self._select_all_item, checked)
        finally:
            self._item_model.blockSignals(False)
        self._refresh_display()
        self._notify_if_changed()

    def _sync_select_all_row(self) -> None:
        """Deja la fila "Todas" en su estado -marcada, desmarcada o a medio
        marcar- según lo que haya realmente marcado debajo, sin que eso
        cuente como un clic sobre ella."""
        if self._select_all_item is None:
            return
        items = self._data_items()
        if not items or not any(self._is_checked(item) for item in items):
            estado = Qt.CheckState.Unchecked
        elif all(self._is_checked(item) for item in items):
            estado = Qt.CheckState.Checked
        else:
            estado = Qt.CheckState.PartiallyChecked
        if self._select_all_item.checkState() == estado:
            return
        self._updating_select_all = True
        try:
            self._select_all_item.setCheckState(estado)
        finally:
            self._updating_select_all = False

    def _notify_if_changed(self) -> None:
        actual = tuple(self.selected_values())
        if actual != self._previous_selection:
            self._previous_selection = actual
            self.selection_changed.emit()

    # -- texto mostrado ---------------------------------------------------

    def _refresh_display(self) -> None:
        self.setToolTip(", ".join(self.selected_texts()) or self._none_text)
        self.update()

    def _display_text(self) -> str:
        items = self._data_items()
        if not items:
            return self._none_text
        seleccionados = self.selected_texts()
        if len(seleccionados) == len(items):
            return self._all_text
        if not seleccionados:
            return self._none_text
        junto = ", ".join(seleccionados)
        disponible = self.width() - _ARROW_WIDTH_PX
        if self.fontMetrics().horizontalAdvance(junto) <= disponible:
            return junto
        return f"{len(seleccionados)} de {len(items)}"

    def paintEvent(self, event) -> None:
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = self._display_text()
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
        painter.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, option)
