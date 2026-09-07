"""Estado de la pestaña de ciclos que no es un widget: filtros, paginación y
los ciclos de la página actual. Sin PySide6 -la página lo muta y se repinta
desde él por un único `_refresh()` propio (ver `SteriflowDataPage`)-.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path
from typing import Sequence

from src.modules.steriflow.logic.config import load_settings
from src.modules.steriflow.logic.sterilization import service as sterilization_service
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle
from src.modules.steriflow.logic.sterilization.queries import CycleFilters, CyclePage, cycle_page

DEFAULT_PAGE_SIZE = 50


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_temp(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


class SteriflowDataPresenter:
    def __init__(self, page_size: int = DEFAULT_PAGE_SIZE) -> None:
        self._filters = CycleFilters()
        self._page_size = page_size
        self._page_index = 0
        self._page = CyclePage(cycles=[], total=0, page_index=0, page_size=page_size)

    # --- filtros: todos vuelven a la primera página, igual que hoy hace
    # _on_filters_changed() ---

    def set_product_query(self, text: str | None) -> None:
        self._filters = dataclasses.replace(self._filters, product_query=text or None)
        self._page_index = 0

    def set_date_range(self, date_from: dt.date | None, date_to: dt.date | None) -> None:
        self._filters = dataclasses.replace(self._filters, date_from=date_from, date_to=date_to)
        self._page_index = 0

    def set_needs_review(self, only_pending: bool) -> None:
        self._filters = dataclasses.replace(self._filters, needs_review=True if only_pending else None)
        self._page_index = 0

    def clear_filters(self) -> None:
        self._filters = CycleFilters()
        self._page_index = 0

    # --- paginación ---

    def set_page_size(self, size: int) -> None:
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
            return "Sin ciclos"
        first = self._page_index * self._page_size + 1
        last = min(first + self._page_size - 1, self._page.total)
        return f"Mostrando {first}–{last} de {self._page.total}"

    # --- datos ---

    def reload(self) -> None:
        self._page = cycle_page(self._filters, page_index=self._page_index, page_size=self._page_size)

    def cycles(self) -> list[SterilizationCycle]:
        return self._page.cycles

    def cycles_at(self, rows: Sequence[int]) -> list[SterilizationCycle]:
        cycles = self._page.cycles
        return [cycles[row] for row in rows if 0 <= row < len(cycles)]

    def cycle_at(self, row: int) -> SterilizationCycle | None:
        cycles = self._page.cycles
        return cycles[row] if 0 <= row < len(cycles) else None

    # --- formateo: las mismas columnas que se ven en pantalla, en texto
    # plano. `row_cells` es lo que pinta la tabla (última celda: "Revisar" o
    # vacío, el detalle va en el tooltip); `print_cells` es lo que va a
    # papel/PDF (última celda: las notas de revisión, sin tooltip posible) ---

    def row_cells(self, cycle: SterilizationCycle) -> list[str]:
        return [
            str(cycle.autoclave_code),
            cycle.started_at.strftime("%d/%m/%Y %H:%M:%S"),
            cycle.product,
            cycle.batch,
            cycle.cycle_number,
            _format_duration(cycle.sterilization_duration_s),
            _format_temp(cycle.sterilization_temp_mean_c),
            _format_temp(cycle.sterilization_temp_min_c),
            _format_temp(cycle.sterilization_temp_max_c),
            "Revisar" if cycle.needs_review else "",
        ]

    def print_cells(self, cycle: SterilizationCycle) -> list[str]:
        cells = self.row_cells(cycle)
        cells[-1] = cycle.review_notes if cycle.needs_review else ""
        return cells

    # --- PDF ---

    def resolve_pdf(self, cycle: SterilizationCycle) -> Path | None:
        return sterilization_service.find_pdf(load_settings(), cycle.source_filename)
