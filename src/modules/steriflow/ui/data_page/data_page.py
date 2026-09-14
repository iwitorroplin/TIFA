from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.steriflow.logic.logs import agent_logger
from src.modules.steriflow.logic.sterilization.columns import CycleColumn
from src.modules.steriflow.messages import catalog
from src.modules.steriflow.messages.catalog import OpenFailure
from src.modules.steriflow.ui.data_page.data_presenter import SteriflowDataPresenter
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.shared.ui import printing

from src.modules.steriflow.ui.data_page.actions_row import ActionsRow
from src.modules.steriflow.ui.data_page.filters_row import FiltersRow
from src.modules.steriflow.ui.data_page.pagination_row import PaginationRow
from src.modules.steriflow.ui.data_page.print_job import PRINT_PDF_PREFIX, build_print_job

# Fondo y letra se fijan los dos explícitamente: la app puede correr con tema
# claro u oscuro (letra blanca por defecto en oscuro), y un fondo claro con
# letra heredada blanca queda ilegible. Fijando ambos hay contraste siempre.
_REVIEW_BACKGROUND = QColor(255, 244, 200)
_REVIEW_FOREGROUND = QColor(90, 60, 0)


class SteriflowDataPage(QWidget):
    def __init__(self):
        super().__init__()

        self._presenter = SteriflowDataPresenter()

        # Vacío hasta el primer _refresh(): así _apply_visible_columns()
        # siempre reconstruye la tabla la primera vez (ver showEvent).
        self._current_columns: list[CycleColumn] = []

        self._cycles_table = self._build_cycles_table()
        self._filters_row = FiltersRow(self._presenter, self._refresh)
        self._actions_row = ActionsRow(
            self._open_selected_pdfs, self._print_selected, self._export_selected_to_pdf
        )
        self._pagination_row = PaginationRow(
            self._presenter, self._on_page_size_changed, self._go_previous_page, self._go_next_page
        )

        group = QGroupBox("Ciclos de esterilización")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._filters_row)
        group_layout.addWidget(self._cycles_table)
        group_layout.addWidget(self._actions_row)
        group_layout.addWidget(self._pagination_row)

        layout = QVBoxLayout(self)
        layout.addWidget(group)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _build_cycles_table(self):
        # Sin columnas todavía: `_apply_visible_columns()` fija el número y
        # las cabeceras en el primer `_refresh()` (disparado por showEvent),
        # según la configuración de columnas visibles.
        table = QTableWidget(0, 0)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.cellDoubleClicked.connect(self._on_row_double_clicked)
        return table

    def _on_page_size_changed(self, size):
        self._presenter.set_page_size(size)
        self._refresh()

    def _go_previous_page(self):
        if self._presenter.go_previous():
            self._refresh()

    def _go_next_page(self):
        if self._presenter.go_next():
            self._refresh()

    def _refresh(self):
        self._filters_row.apply_to_presenter()
        self._presenter.reload()

        table = self._cycles_table
        columns = self._apply_visible_columns()
        # Autoclave y Revisión son columnas fijas: siempre están presentes en
        # `columns`, así que en la práctica esto nunca da None. El guard es
        # defensivo por si `CYCLE_COLUMNS` cambiara alguna vez.
        autoclave_col = self._column_index(columns, "autoclave")
        review_col = self._column_index(columns, "review")

        table.setRowCount(0)
        for cycle in self._presenter.cycles():
            row = table.rowCount()
            table.insertRow(row)
            self._set_cycle_row(row, cycle, autoclave_col, review_col)

        self._pagination_row.repaint()

    def _apply_visible_columns(self) -> list[CycleColumn]:
        """Ajusta la tabla (número de columnas, cabeceras, anchos) a las
        columnas configuradas, solo cuando cambian -no hace falta reconstruir
        la cabecera en cada refresco de filas."""
        columns = self._presenter.visible_columns()
        if columns == self._current_columns:
            return columns
        self._current_columns = columns

        table = self._cycles_table
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([col.header for col in columns])

        header = table.horizontalHeader()
        for index, col in enumerate(columns):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if col.key == "product"
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(index, mode)

        return columns

    @staticmethod
    def _column_index(columns: list[CycleColumn], key: str) -> int | None:
        for index, col in enumerate(columns):
            if col.key == key:
                return index
        return None

    def _set_cycle_row(self, row, cycle, autoclave_col, review_col):
        table = self._cycles_table
        for col, text in enumerate(self._presenter.row_cells(cycle)):
            table.setItem(row, col, QTableWidgetItem(text))

        # El número que imprime el informe va en el tooltip y no en una columna
        # propia: solo hace falta para entender por qué un PDF MPI_10_* sale
        # como AUTOCLAVE8, y no merece ensanchar la tabla.
        aviso_codigo = self._presenter.autoclave_tooltip(cycle)
        if aviso_codigo and autoclave_col is not None:
            table.item(row, autoclave_col).setToolTip(aviso_codigo)

        if cycle.needs_review:
            if review_col is not None:
                table.item(row, review_col).setToolTip(cycle.review_notes)
            for col in range(table.columnCount()):
                item = table.item(row, col)
                item.setBackground(_REVIEW_BACKGROUND)
                item.setForeground(_REVIEW_FOREGROUND)

    def _selected_cycles(self):
        rows = sorted({index.row() for index in self._cycles_table.selectionModel().selectedRows()})
        return self._presenter.cycles_at(rows)

    def _on_row_double_clicked(self, row, column):
        cycle = self._presenter.cycle_at(row)
        if cycle is not None:
            self._open_pdfs([cycle])

    def _open_selected_pdfs(self):
        cycles = self._selected_cycles()
        if not cycles:
            push(Module.STERIFLOW, catalog.no_cycles_selected_to_open())
            return
        self._open_pdfs(cycles)

    def _open_pdfs(self, cycles):
        fallos = []
        for cycle in cycles:
            ruta = self._presenter.resolve_pdf(cycle)
            if ruta is None:
                fallos.append((cycle.source_filename, OpenFailure.NOT_FOUND))
            elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta))):
                fallos.append((cycle.source_filename, OpenFailure.CANNOT_OPEN))

        if fallos:
            push(Module.STERIFLOW, catalog.pdfs_not_opened(fallos))

    def _print_selected(self):
        cycles = self._selected_cycles()
        if not cycles:
            push(Module.STERIFLOW, catalog.no_cycles_selected_to_print())
            return

        build_print_job(self._presenter, cycles).preview(self)

    def _export_selected_to_pdf(self):
        cycles = self._selected_cycles()
        if not cycles:
            push(Module.STERIFLOW, catalog.no_cycles_selected_to_export())
            return

        destino = printing.ask_pdf_path(self, f"{PRINT_PDF_PREFIX}_{dt.datetime.now():%Y%m%d_%H%M}.pdf")
        if destino is None:
            return

        # Un PDF exportado es un documento que sale de la aplicación: interesa
        # que quede en el log cuándo se generó y dónde, no solo avisar en el
        # momento.
        logger = agent_logger()
        try:
            build_print_job(self._presenter, cycles).export_pdf(destino)
        except OSError as ex:
            announce(logger, catalog.cycles_pdf_save_failed(destino, ex))
            return

        announce(logger, catalog.cycles_pdf_saved(len(cycles), destino))
