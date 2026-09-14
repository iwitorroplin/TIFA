"""`MultiSelectComboBox`: contenido y selección, sin dominio de por medio
-nada de autoclaves ni máquinas aquí, eso lo prueban Ferlo y Steriflow por su
lado sobre sus propios filtros-.

Corre sin pantalla (`QT_QPA_PLATFORM=offscreen`, como el resto de la suite:
ver el docstring de `tests/test_architecture.py`). No simula clics de ratón
sobre el desplegable abierto -eso exigiría posicionar la vista de verdad y
sería frágil en headless-, así que solo se ejercita la API pública
(`select_all`, `set_selected_values`...), que es por donde pasa cualquier
interacción real antes de llegar al modelo.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from src.shared.ui.components.multi_select_combo_box import MultiSelectComboBox


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def combo(qapp):
    widget = MultiSelectComboBox()
    widget.add_item("Autoclave 1", 1)
    widget.add_item("Autoclave 2", 2)
    widget.add_item("Autoclave 3", 3)
    return widget


def test_add_item_usa_el_texto_como_valor_si_no_se_indica(qapp):
    widget = MultiSelectComboBox()
    widget.add_item("F1")
    assert widget.selected_values() == []
    widget.select_all()
    assert widget.selected_values() == ["F1"]


def test_add_item_rechaza_valores_repetidos(combo):
    with pytest.raises(ValueError):
        combo.add_item("Autoclave 1 bis", 1)


def test_set_selected_values_y_lectura(combo):
    combo.set_selected_values([1, 3])
    assert combo.selected_values() == [1, 3]
    assert combo.selected_texts() == ["Autoclave 1", "Autoclave 3"]
    assert combo.is_all_selected() is False


def test_select_all_y_deselect_all(combo):
    combo.select_all()
    assert combo.selected_values() == [1, 2, 3]
    assert combo.is_all_selected() is True

    combo.deselect_all()
    assert combo.selected_values() == []
    assert combo.is_all_selected() is False


def test_selection_changed_se_emite_una_vez_por_cambio_real(combo):
    cambios = []
    combo.selection_changed.connect(lambda: cambios.append(tuple(combo.selected_values())))

    combo.select_all()
    assert cambios == [(1, 2, 3)]

    combo.select_all()  # ya estaban todas: no hay cambio real, no reemite
    assert cambios == [(1, 2, 3)]

    combo.set_selected_values([2])
    assert cambios == [(1, 2, 3), (2,)]


def test_remove_item_y_clear_items(combo):
    combo.select_all()
    combo.remove_item(2)
    assert combo.selected_values() == [1, 3]

    combo.clear_items()
    assert combo.selected_values() == []
    assert combo.is_all_selected() is False


def test_tooltip_refleja_la_seleccion(combo):
    combo.deselect_all()
    assert combo.toolTip() == "Ninguna"

    combo.set_selected_values([2])
    assert combo.toolTip() == "Autoclave 2"

    combo.select_all()
    assert combo.toolTip() == "Autoclave 1, Autoclave 2, Autoclave 3"
