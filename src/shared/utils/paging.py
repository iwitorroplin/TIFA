"""Una página de resultados y la forma de pedirla, sin saber de qué dominio
son las filas.

Genérico a propósito, igual que `csv_format.py`: cada módulo define sus propios
filtros y su propia consulta (`cycle_page` en Steriflow y en Ferlo), pero todos
devuelven un `Page[T]`, así que la paginación de la interfaz
(`src/shared/ui/paged_view_model.py`) se escribe una sola vez.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")
F_contra = TypeVar("F_contra", contravariant=True)


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    # Cuántas filas hay en total con ese filtro, no cuántas trae esta página.
    total: int
    page_index: int
    page_size: int


class PageQuery(Protocol[F_contra, T]):
    """Firma de las consultas paginadas: `cycle_page(filters, page_index=..., page_size=...)`."""

    def __call__(self, filters: F_contra, *, page_index: int, page_size: int) -> Page[T]: ...
