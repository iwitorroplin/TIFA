"""Consultas de ciclos listas para pintar la pestaña de ciclos (Fase 4):
abre y cierra la conexión aquí, igual que
`src/modules/steriflow/logic/sterilization/queries.py` -así ningún widget ni
view model tiene que llamar a `connect()` por su cuenta.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Sequence

from src.shared.db.connection import connect
from src.shared.utils.paging import Page

from . import repo
from .repo import CycleRow


@dataclass(frozen=True)
class CycleFilters:
    # None = todas las máquinas, sin filtrar; una secuencia vacía (combo con
    # todas las máquinas desmarcadas) es un filtro real que no debe casar con
    # ningún ciclo -ver `repo._cycle_filters_sql`-.
    machines: Sequence[str] | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    needs_review: bool | None = None


def cycle_page(filters: CycleFilters, *, page_index: int, page_size: int) -> Page[CycleRow]:
    """Una página de ciclos y cuántos hay en total con ese filtro.

    Una sola conexión para el COUNT y el SELECT, igual que en Steriflow: los
    dos comparten el mismo filtro y así no hay ventana entre uno y otro en la
    que el total pueda quedar desincronizado de la página.
    """
    conn = connect()
    try:
        total = repo.count_cycles(
            conn,
            machines=filters.machines,
            date_from=filters.date_from,
            date_to=filters.date_to,
            needs_review=filters.needs_review,
        )
        cycles = repo.list_cycles(
            conn,
            machines=filters.machines,
            date_from=filters.date_from,
            date_to=filters.date_to,
            needs_review=filters.needs_review,
            limit=page_size,
            offset=page_index * page_size,
        )
    finally:
        conn.close()

    return Page(items=cycles, total=total, page_index=page_index, page_size=page_size)


def cycle_detail(cycle_id: int):
    """Un ciclo con sus muestras e incidencias, para el diálogo de detalle."""
    conn = connect()
    try:
        cycle = repo.get_cycle(conn, cycle_id)
        if cycle is None:
            return None, [], []
        samples = repo.list_samples(conn, cycle_id)
        incidents = repo.list_incidents(conn, cycle_id)
        return cycle, samples, incidents
    finally:
        conn.close()
