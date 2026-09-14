"""View model de la pestaña de Ciclos de Ferlo: filtros propios y las celdas
de la tabla. La paginación y el estado común viven en
`src/shared/ui/paged_view_model.py`, igual que en
`src/modules/steriflow/ui/data_page/data_view_model.py`.
"""

from __future__ import annotations

import datetime as dt
from typing import Sequence

from src.modules.ferlo.logic.analysis.models import ManualVerdict
from src.modules.ferlo.logic.analysis.queries import CycleFilters, cycle_page
from src.modules.ferlo.logic.analysis.repo import CycleRow
from src.modules.ferlo.messages import catalog
from src.shared.ui.paged_view_model import PagedViewModel
from src.shared.utils.formatting import MISSING, format_datetime, format_decimal


class FerloDataViewModel(PagedViewModel[CycleFilters, CycleRow]):
    def __init__(self) -> None:
        super().__init__(cycle_page, CycleFilters, empty_label="Sin ciclos")

    # --- filtros ---

    def set_machines(self, machines: Sequence[str] | None) -> None:
        """None = sin filtrar (combo con "Todas" marcado); una secuencia
        vacía es un filtro real que no debe casar con ningún ciclo (ver
        `logic/analysis/repo.py:_cycle_filters_sql`) -aquí ya no se colapsa
        a None, es `FiltersRow` quien decide con `combo.is_all_selected()`."""
        self.update_filters(machines=tuple(machines) if machines is not None else None)

    def set_date_range(self, date_from: dt.date | None, date_to: dt.date | None) -> None:
        self.update_filters(date_from=date_from, date_to=date_to)

    def set_needs_review(self, only_pending: bool) -> None:
        self.update_filters(needs_review=True if only_pending else None)

    # --- formateo: las columnas que pinta la tabla ---

    def row_cells(self, cycle: CycleRow) -> list[str]:
        # Las dos duraciones, y la de esterilización primero: es la que se
        # mira. Antes solo estaba la del ciclo entero bajo el rótulo
        # "Duración", que se leía como si fuera la de la esterilización y es
        # casi un 30 % mayor.
        return [
            cycle.machine,
            format_datetime(cycle.started_at),
            f"{cycle.program_code:02d} · {cycle.program_name}" if cycle.program_code else MISSING,
            format_decimal(cycle.sterilization_duration_min, 1),
            format_decimal(cycle.duration_min, 1),
            format_decimal(cycle.mean_temperature_c, 2),
            format_decimal(cycle.mean_stable_temperature_c, 2),
            catalog.status_label(cycle.status),
            catalog.verdict_label(ManualVerdict(cycle.manual_verdict)),
        ]
