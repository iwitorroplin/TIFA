"""Estado de la pestaña de Ciclos que no es un widget: filtros, paginación y
los ciclos de la página actual. Sin PySide6 -la página lo muta y se repinta
desde él por un único `_refresh()` propio-, mismo patrón que
`src/modules/steriflow/ui/data_presenter.py`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Sequence

from src.modules.ferlo.logic.analysis.models import ManualVerdict
from src.modules.ferlo.logic.analysis.queries import CycleFilters, CyclePage, cycle_page
from src.modules.ferlo.logic.analysis.repo import CycleRow
from src.modules.ferlo.messages import catalog

DEFAULT_PAGE_SIZE = 50


def _fmt_temp(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _fmt_min(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}"


class FerloDataPresenter:
    def __init__(self, page_size: int = DEFAULT_PAGE_SIZE) -> None:
        self._filters = CycleFilters()
        self._page_size = page_size
        self._page_index = 0
        self._page = CyclePage(cycles=[], total=0, page_index=0, page_size=page_size)

    # --- filtros: todos vuelven a la primera pagina ---

    def set_machine(self, machine: str | None) -> None:
        self._filters = dataclasses.replace(self._filters, machine=machine or None)
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

    # --- paginacion ---

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

    def cycles(self) -> list[CycleRow]:
        return self._page.cycles

    def cycles_at(self, rows: Sequence[int]) -> list[CycleRow]:
        cycles = self._page.cycles
        return [cycles[row] for row in rows if 0 <= row < len(cycles)]

    def cycle_at(self, row: int) -> CycleRow | None:
        cycles = self._page.cycles
        return cycles[row] if 0 <= row < len(cycles) else None

    # --- formateo: las columnas que pinta la tabla ---

    def row_cells(self, cycle: CycleRow) -> list[str]:
        return [
            cycle.machine,
            cycle.started_at.strftime("%d/%m/%Y %H:%M:%S"),
            f"{cycle.program_code:02d} · {cycle.program_name}" if cycle.program_code else "—",
            _fmt_min(cycle.duration_min),
            _fmt_temp(cycle.mean_temperature_c),
            _fmt_temp(cycle.mean_stable_temperature_c),
            catalog.status_label(cycle.status),
            catalog.verdict_label(ManualVerdict(cycle.manual_verdict)),
        ]
