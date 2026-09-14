"""Paginación y filtros de `PagedViewModel`, sin Qt ni base de datos: la
consulta es una lista en memoria con la misma firma que `cycle_page`."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.shared.ui.paged_view_model import PagedViewModel
from src.shared.utils.paging import Page


@dataclass(frozen=True)
class _Filters:
    only_even: bool = False
    codes: tuple[int, ...] | list[int] | None = None


def _query_over(rows: list[int]):
    def query(filters: _Filters, *, page_index: int, page_size: int) -> Page[int]:
        filtered = [r for r in rows if not filters.only_even or r % 2 == 0]
        start = page_index * page_size
        return Page(
            items=filtered[start:start + page_size],
            total=len(filtered),
            page_index=page_index,
            page_size=page_size,
        )

    return query


@pytest.fixture
def vm():
    view_model = PagedViewModel(_query_over(list(range(25))), _Filters, empty_label="Sin filas", page_size=10)
    view_model.reload()
    return view_model


def test_primera_pagina_sin_anterior_y_con_siguiente(vm):
    assert vm.items() == list(range(10))
    assert not vm.can_go_previous()
    assert vm.can_go_next()
    assert vm.pagination_label() == "Mostrando 1–10 de 25"


def test_ultima_pagina_parcial(vm):
    assert vm.go_next()
    vm.reload()
    assert vm.go_next()
    vm.reload()

    assert vm.items() == [20, 21, 22, 23, 24]
    assert not vm.can_go_next()
    assert not vm.go_next()
    assert vm.pagination_label() == "Mostrando 21–25 de 25"


def test_en_la_primera_pagina_no_se_puede_retroceder(vm):
    assert not vm.go_previous()


def test_volcar_los_mismos_filtros_no_devuelve_a_la_primera_pagina(vm):
    """La página vuelca todos sus filtros antes de cada refresco, también al
    pasar de página: si eso reseteara el índice, "Siguiente" no avanzaría.
    Con una lista nueva pero igual (lo que devuelve cada vez un grupo de
    checkboxes) tampoco cuenta como cambio."""
    vm.update_filters(only_even=False, codes=[1, 2])
    vm.reload()

    for expected in (list(range(10, 20)), [20, 21, 22, 23, 24]):
        assert vm.go_next()
        vm.update_filters(only_even=False, codes=[1, 2])
        vm.reload()
        assert vm.items() == expected


def test_cambiar_un_filtro_vuelve_a_la_primera_pagina(vm):
    vm.go_next()
    vm.update_filters(only_even=True)
    vm.reload()

    assert vm.items() == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
    assert vm.pagination_label() == "Mostrando 1–10 de 13"


def test_limpiar_filtros_vuelve_a_la_primera_pagina(vm):
    vm.update_filters(only_even=True)
    vm.go_next()
    vm.clear_filters()
    vm.reload()

    assert vm.items() == list(range(10))


def test_cambiar_tamano_de_pagina_vuelve_a_la_primera(vm):
    vm.go_next()
    vm.set_page_size(20)
    vm.reload()

    assert vm.items() == list(range(20))


def test_mismo_tamano_de_pagina_no_mueve_la_pagina(vm):
    vm.go_next()
    vm.set_page_size(10)
    vm.reload()

    assert vm.items() == list(range(10, 20))


def test_sin_resultados_usa_la_etiqueta_vacia():
    vm = PagedViewModel(_query_over([]), _Filters, empty_label="Sin filas")
    vm.reload()

    assert vm.pagination_label() == "Sin filas"
    assert not vm.can_go_next()


def test_acceso_por_fila_ignora_indices_fuera_de_rango(vm):
    assert vm.item_at(3) == 3
    assert vm.item_at(10) is None
    assert vm.item_at(-1) is None
    assert vm.items_at([0, 99, 2, -1]) == [0, 2]
