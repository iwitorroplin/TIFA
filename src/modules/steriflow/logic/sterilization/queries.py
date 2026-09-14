"""Consultas de ciclos de esterilización listas para pintar una página de
tabla: abre y cierra la conexión aquí, para que ningún widget ni presenter
tenga que llamar a `connect()` por su cuenta."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Sequence

from src.shared.db.connection import connect
from src.modules.steriflow.logic.sterilization import repo
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle


@dataclass(frozen=True)
class CycleFilters:
    product_query: str | None = None
    # Números reales de autoclave (6..9) a mostrar, no el que imprime el
    # informe: es el que se guarda en el ciclo (ver
    # `logic/sterilization/service.py`). None o vacío = todas, sin filtrar.
    autoclave_codes: Sequence[int] | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    needs_review: bool | None = None
    # Dirección de started_at DENTRO de cada grupo de autoclave. El agrupado
    # por autoclave (ascendente) ya no es opcional -se aplica siempre en
    # `repo.list_cycles`-, así que esto es lo único que queda por elegir.
    # False (por defecto) = más reciente primero.
    started_at_ascending: bool = False


@dataclass(frozen=True)
class CyclePage:
    cycles: list[SterilizationCycle]
    total: int
    page_index: int
    page_size: int


def cycle_page(filters: CycleFilters, *, page_index: int, page_size: int) -> CyclePage:
    """Una página de ciclos y cuántos hay en total con ese filtro.

    Una sola conexión para el COUNT y el SELECT: los dos comparten el mismo
    filtro, y así no hay ventana entre uno y otro en la que el total pueda
    quedar desincronizado de la página.
    """
    conn = connect()
    try:
        total = repo.count_cycles(
            conn,
            product_query=filters.product_query,
            autoclave_codes=filters.autoclave_codes,
            date_from=filters.date_from,
            date_to=filters.date_to,
            needs_review=filters.needs_review,
        )
        cycles = repo.list_cycles(
            conn,
            product_query=filters.product_query,
            autoclave_codes=filters.autoclave_codes,
            date_from=filters.date_from,
            date_to=filters.date_to,
            needs_review=filters.needs_review,
            started_at_ascending=filters.started_at_ascending,
            limit=page_size,
            offset=page_index * page_size,
        )
    finally:
        conn.close()

    return CyclePage(cycles=cycles, total=total, page_index=page_index, page_size=page_size)
