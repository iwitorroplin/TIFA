"""Estado de una tabla paginada que no es un widget: filtros, paginación y las
filas de la página actual. Sin PySide6 -la página lo muta y se repinta desde
él por un único `_refresh()` propio-.

Es un view model y no un presenter: no conoce la vista ni le empuja nada; es
la página la que lo lee cuando decide repintar. Cada módulo hereda de aquí
(`FerloDataViewModel`, `SteriflowDataViewModel`) y solo añade sus setters de
filtro y cómo se formatea una fila.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Generic, Sequence, TypeVar

from src.shared.utils.paging import Page, PageQuery

DEFAULT_PAGE_SIZE = 50

F = TypeVar("F")
T = TypeVar("T")


class PagedViewModel(Generic[F, T]):
    def __init__(
        self,
        query: PageQuery[F, T],
        filters_factory: Callable[[], F],
        *,
        empty_label: str,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> None:
        self._query = query
        self._filters_factory = filters_factory
        self._empty_label = empty_label
        self._filters = filters_factory()
        self._page_size = page_size
        self._page_index = 0
        self._page: Page[T] = Page(items=[], total=0, page_index=0, page_size=page_size)

    # --- filtros: un cambio real vuelve a la primera página ---

    def update_filters(self, **changes: Any) -> None:
        """Solo vuelve a la primera página si el filtro cambia de verdad. La
        página vuelca TODOS los filtros de sus widgets antes de cada refresco
        -también al pasar de página-, así que resetear siempre dejaría
        "Siguiente" devolviendo a la página 1."""
        filters = dataclasses.replace(self._filters, **changes)
        if filters != self._filters:
            self._filters = filters
            self._page_index = 0

    def clear_filters(self) -> None:
        self._filters = self._filters_factory()
        self._page_index = 0

    # --- paginación ---

    def set_page_size(self, size: int) -> None:
        if size != self._page_size:
            self._page_size = size
            self._page_index = 0

    def can_go_previous(self) -> bool:
        return self._page_index > 0

    def can_go_next(self) -> bool:
        return (self._page_index + 1) * self._page_size < self._page.total

    def go_previous(self) -> bool:
        if not self.can_go_previous():
            return False
        self._page_index -= 1
        return True

    def go_next(self) -> bool:
        if not self.can_go_next():
            return False
        self._page_index += 1
        return True

    def pagination_label(self) -> str:
        if self._page.total == 0:
            return self._empty_label
        first = self._page_index * self._page_size + 1
        last = min(first + self._page_size - 1, self._page.total)
        return f"Mostrando {first}–{last} de {self._page.total}"

    # --- datos ---

    def reload(self) -> None:
        self._page = self._query(self._filters, page_index=self._page_index, page_size=self._page_size)

    def items(self) -> list[T]:
        return self._page.items

    def items_at(self, rows: Sequence[int]) -> list[T]:
        items = self._page.items
        return [items[row] for row in rows if 0 <= row < len(items)]

    def item_at(self, row: int) -> T | None:
        items = self._page.items
        return items[row] if 0 <= row < len(items) else None
