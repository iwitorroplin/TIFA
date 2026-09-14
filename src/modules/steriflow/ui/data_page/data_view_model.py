"""View model de la pestaña de ciclos de Steriflow: filtros propios, columnas
visibles, celdas de pantalla e impresión y PDF de origen. La paginación y el
estado común viven en `src/shared/ui/paged_view_model.py`.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Sequence

from src.modules.steriflow.logic.config import load_settings
from src.modules.steriflow.logic.sterilization import service as sterilization_service
from src.modules.steriflow.logic.sterilization.columns import CYCLE_COLUMNS, CycleColumn
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle
from src.modules.steriflow.logic.sterilization.queries import CycleFilters, cycle_page
from src.shared.ui.paged_view_model import PagedViewModel


class SteriflowDataViewModel(PagedViewModel[CycleFilters, SterilizationCycle]):
    def __init__(self) -> None:
        super().__init__(cycle_page, CycleFilters, empty_label="Sin ciclos")

    # --- filtros ---

    def set_product_query(self, text: str | None) -> None:
        self.update_filters(product_query=text or None)

    def set_autoclave_codes(self, codes: Sequence[int] | None) -> None:
        """None = sin filtrar (combo con "Todas" marcado); una secuencia
        vacía es un filtro real que no debe casar con ningún ciclo (ver
        `logic/sterilization/repo.py:_build_filters`) -aquí ya no se colapsa
        a None, es `FiltersRow` quien decide con `combo.is_all_selected()`."""
        self.update_filters(autoclave_codes=tuple(codes) if codes is not None else None)

    def set_started_at_ascending(self, ascending: bool) -> None:
        """Dirección de `started_at` dentro de cada grupo de autoclave (el
        agrupado en sí ya no es opcional, ver `repo.list_cycles`). Vuelve a la
        primera página igual que un filtro: con otro orden, la página en la
        que estabas ya no contiene las mismas filas."""
        self.update_filters(started_at_ascending=ascending)

    def set_date_range(self, date_from: dt.date | None, date_to: dt.date | None) -> None:
        self.update_filters(date_from=date_from, date_to=date_to)

    def set_needs_review(self, only_pending: bool) -> None:
        self.update_filters(needs_review=True if only_pending else None)

    def autoclaves(self) -> list[tuple[str, int]]:
        """(nombre, código) de las autoclaves configuradas, para el filtro. Se
        leen de la configuración y no de los ciclos guardados: una autoclave
        recién dada de alta también tiene que poder elegirse."""
        return [(a.name, a.code) for a in load_settings().autoclaves]

    # --- columnas: mismo conjunto para pantalla e impresión, filtrado según
    # la configuración guardada (ver logic/sterilization/columns.py) ---

    def visible_columns(self) -> list[CycleColumn]:
        """Las columnas a pintar, en orden canónico: las fijas siempre, más
        las opcionales activas en la configuración. Se relee `load_settings()`
        en cada llamada -igual que `autoclaves()`- para que una configuración
        de columnas recién guardada se refleje sin necesitar una señal de
        invalidación aparte."""
        enabled = load_settings().columns.visible_keys
        return [col for col in CYCLE_COLUMNS if col.fixed or col.key in enabled]

    def row_cells(self, cycle: SterilizationCycle) -> list[str]:
        """Lo que pinta la tabla en pantalla."""
        return [col.cell(cycle) for col in self.visible_columns()]

    def print_cells(self, cycle: SterilizationCycle) -> list[str]:
        """Lo que va a papel/PDF: igual que `row_cells`, salvo la celda de
        Revisión, que en pantalla es "Revisar"/vacío (con el detalle en un
        tooltip) y aquí son las notas completas -en papel no hay tooltip
        posible-. Se localiza por clave y no por posición: así una columna
        movida o desactivada nunca sustituye la celda equivocada."""
        cells = self.row_cells(cycle)
        review_index = self._review_column_index()
        if review_index is not None:
            cells[review_index] = cycle.review_notes if cycle.needs_review else ""
        return cells

    def _review_column_index(self) -> int | None:
        for index, col in enumerate(self.visible_columns()):
            if col.key == "review":
                return index
        return None

    def autoclave_tooltip(self, cycle: SterilizationCycle) -> str:
        """Qué número imprime el informe, cuando no es el de la máquina: es lo
        que explica que un PDF llamado MPI_10_* salga aquí como AUTOCLAVE8."""
        if cycle.reported_code is None or cycle.reported_code == cycle.autoclave_code:
            return ""
        return f"El informe imprime «Cód. Autoclave {cycle.reported_code}»"

    # --- PDF ---

    def resolve_pdf(self, cycle: SterilizationCycle) -> Path | None:
        return sterilization_service.find_pdf(load_settings(), cycle.source_filename)
