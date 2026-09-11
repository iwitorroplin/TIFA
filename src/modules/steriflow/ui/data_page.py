from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QDate, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.steriflow.logic.logs import agent_logger
from src.modules.steriflow.messages import catalog
from src.modules.steriflow.messages.catalog import OpenFailure
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.modules.steriflow.ui.data_presenter import DEFAULT_PAGE_SIZE, SteriflowDataPresenter
from src.shared.ui.components.app_button import AppButton
from src.shared.ui import printing

_COL_AUTOCLAVE = 0
_COL_STARTED_AT = 1
_COL_PRODUCT = 2
_COL_CYCLE_NUMBER = 3
_COL_PHASE = 4
_COL_DURATION = 5
_COL_TEMP_MEAN = 6
_COL_TEMP_MIN = 7
_COL_TEMP_MAX = 8
_COL_REVIEW = 9

_HEADERS = [
    "Autoclave",
    "Fecha inicio",
    "Producto",
    "Nº ciclo",
    "Fase esterilización",
    "Duración esterilización",
    "T media (°C)",
    "T mín (°C)",
    "T máx (°C)",
    "Revisión",
]

# Fondo y letra se fijan los dos explícitamente: la app puede correr con tema
# claro u oscuro (letra blanca por defecto en oscuro), y un fondo claro con
# letra heredada blanca queda ilegible. Fijando ambos hay contraste siempre.
_REVIEW_BACKGROUND = QColor(255, 244, 200)
_REVIEW_FOREGROUND = QColor(90, 60, 0)

_PRINT_TITLE = "Ciclos de esterilización — Steriflow"
_PRINT_PDF_PREFIX = "ciclos_esterilizacion"
# Los números se leen mejor alineados a la derecha; el resto, a la izquierda.
_PRINT_ALIGNS = [
    printing.Align.LEFT,    # Autoclave
    printing.Align.LEFT,    # Fecha inicio
    printing.Align.LEFT,    # Producto
    printing.Align.RIGHT,   # Nº ciclo
    printing.Align.LEFT,    # Fase esterilización
    printing.Align.RIGHT,   # Duración
    printing.Align.RIGHT,   # T media
    printing.Align.RIGHT,   # T mín
    printing.Align.RIGHT,   # T máx
    printing.Align.LEFT,    # Revisión
]

# Orden de la consulta. Ordenar pinchando la cabecera engañaría: la tabla trae
# una página de la base de datos cada vez, así que solo reordenaría las filas
# visibles. Estas dos opciones se aplican en SQL, sobre el conjunto entero.
_SORT_OPTIONS = [
    ("Fecha (reciente primero)", False),
    ("Autoclave y fecha", True),
]
# Por defecto se ordena por autoclave y fecha, que es como se busca un ciclo
# concreto la mayoría de las veces.
_DEFAULT_SORT_INDEX = 1

_PAGE_SIZES = [20, 50, 100]
# Al escribir en el filtro de producto se espera a que el usuario pare de
# teclear antes de volver a consultar la base de datos, para no lanzar una
# consulta por cada letra.
_FILTER_DEBOUNCE_MS = 300


class SteriflowDataPage(QWidget):
    def __init__(self):
        super().__init__()

        self._presenter = SteriflowDataPresenter()

        self._filter_debounce = QTimer(self)
        self._filter_debounce.setSingleShot(True)
        self._filter_debounce.setInterval(_FILTER_DEBOUNCE_MS)
        self._filter_debounce.timeout.connect(self._on_filters_changed)

        self._cycles_table = self._build_cycles_table()

        group = QGroupBox("Ciclos de esterilización")
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._build_filters_row())
        group_layout.addWidget(self._cycles_table)
        group_layout.addWidget(self._build_actions_row())
        group_layout.addWidget(self._build_pagination_row())

        layout = QVBoxLayout(self)
        layout.addWidget(group)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _build_cycles_table(self):
        table = QTableWidget(0, len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(_COL_PRODUCT, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.cellDoubleClicked.connect(self._on_row_double_clicked)
        return table

    def _build_filters_row(self):
        self._product_filter_edit = QLineEdit()
        self._product_filter_edit.setPlaceholderText("Buscar producto...")
        self._product_filter_edit.textChanged.connect(self._filter_debounce.start)

        self._autoclave_combo = QComboBox()
        self._autoclave_combo.addItem("Todas", userData=None)
        for nombre, codigo in self._presenter.autoclaves():
            self._autoclave_combo.addItem(nombre, userData=codigo)
        self._autoclave_combo.currentIndexChanged.connect(self._on_filters_changed)

        self._sort_combo = QComboBox()
        for etiqueta, by_autoclave in _SORT_OPTIONS:
            self._sort_combo.addItem(etiqueta, userData=by_autoclave)
        self._sort_combo.setCurrentIndex(_DEFAULT_SORT_INDEX)
        self._sort_combo.currentIndexChanged.connect(self._on_filters_changed)

        self._date_from_checkbox = QCheckBox("Desde:")
        self._date_from_edit = QDateEdit(QDate.currentDate())
        self._date_from_edit.setCalendarPopup(True)
        self._date_from_edit.setEnabled(False)
        self._date_from_edit.dateChanged.connect(self._on_filters_changed)

        self._date_to_checkbox = QCheckBox("Hasta:")
        self._date_to_edit = QDateEdit(QDate.currentDate())
        self._date_to_edit.setCalendarPopup(True)
        self._date_to_edit.setEnabled(False)
        self._date_to_edit.dateChanged.connect(self._on_filters_changed)

        # Por defecto se filtra desde hoy: abrir la pestaña y ver todo el
        # histórico de golpe es tanto más lento como menos útil que partir del
        # día en curso. Se marca ANTES de conectar `toggled` -si no, dispara
        # `_on_date_filter_toggled`/`_on_filters_changed` en plena
        # construcción, cuando widgets de más abajo en `__init__`
        # (`_needs_review_checkbox`, la tabla, la paginación) todavía no
        # existen-. El enable visual se aplica a mano; el primer `_refresh()`
        # real ya lo hace `showEvent`.
        self._date_from_checkbox.setChecked(True)
        self._date_from_edit.setEnabled(True)

        self._date_from_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_to_checkbox.toggled.connect(self._on_date_filter_toggled)

        self._needs_review_checkbox = QCheckBox("Solo pendientes de revisión")
        self._needs_review_checkbox.toggled.connect(self._on_filters_changed)

        clear_button = AppButton("Limpiar filtros")
        clear_button.clicked.connect(self._clear_filters)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel("Producto:"))
        row_layout.addWidget(self._product_filter_edit)
        row_layout.addWidget(QLabel("Autoclave:"))
        row_layout.addWidget(self._autoclave_combo)
        row_layout.addWidget(QLabel("Ordenar:"))
        row_layout.addWidget(self._sort_combo)
        row_layout.addWidget(self._date_from_checkbox)
        row_layout.addWidget(self._date_from_edit)
        row_layout.addWidget(self._date_to_checkbox)
        row_layout.addWidget(self._date_to_edit)
        row_layout.addWidget(self._needs_review_checkbox)
        row_layout.addWidget(clear_button)
        row_layout.addStretch()
        return row

    def _build_actions_row(self):
        open_pdf_button = AppButton("Abrir PDF")
        open_pdf_button.clicked.connect(self._open_selected_pdfs)

        print_button = AppButton("Imprimir selección")
        print_button.clicked.connect(self._print_selected)

        export_pdf_button = AppButton("Guardar tabla en PDF")
        export_pdf_button.clicked.connect(self._export_selected_to_pdf)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(open_pdf_button)
        row_layout.addWidget(print_button)
        row_layout.addWidget(export_pdf_button)
        row_layout.addStretch()
        return row

    def _build_pagination_row(self):
        self._page_size_combo = QComboBox()
        for size in _PAGE_SIZES:
            self._page_size_combo.addItem(str(size), userData=size)
        self._page_size_combo.setCurrentIndex(_PAGE_SIZES.index(DEFAULT_PAGE_SIZE))
        self._page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)

        self._previous_button = AppButton("< Anterior")
        self._previous_button.clicked.connect(self._go_previous_page)

        self._next_button = AppButton("Siguiente >")
        self._next_button.clicked.connect(self._go_next_page)

        self._pagination_label = QLabel()

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel("Mostrar:"))
        row_layout.addWidget(self._page_size_combo)
        row_layout.addStretch()
        row_layout.addWidget(self._pagination_label)
        row_layout.addWidget(self._previous_button)
        row_layout.addWidget(self._next_button)
        return row

    def _on_date_filter_toggled(self):
        self._date_from_edit.setEnabled(self._date_from_checkbox.isChecked())
        self._date_to_edit.setEnabled(self._date_to_checkbox.isChecked())
        self._on_filters_changed()

    def _clear_filters(self):
        # Los filtros por defecto son fecha (desde hoy) y orden por autoclave,
        # no "sin filtros": es la vista que de verdad se usa al entrar.
        self._filter_debounce.stop()
        self._product_filter_edit.clear()
        self._autoclave_combo.setCurrentIndex(0)
        self._sort_combo.setCurrentIndex(_DEFAULT_SORT_INDEX)
        self._date_from_edit.setDate(QDate.currentDate())
        self._date_to_checkbox.setChecked(False)
        self._needs_review_checkbox.setChecked(False)
        if self._date_from_checkbox.isChecked():
            # Ya estaba marcado: forzar el recálculo, que si no sólo lo
            # dispara el toggled de arriba.
            self._on_filters_changed()
        else:
            self._date_from_checkbox.setChecked(True)

    def _on_filters_changed(self):
        self._presenter.set_product_query(self._product_filter_edit.text().strip())
        self._presenter.set_autoclave_code(self._autoclave_combo.currentData())
        self._presenter.set_by_autoclave(bool(self._sort_combo.currentData()))
        self._presenter.set_date_range(
            self._date_from_edit.date().toPython() if self._date_from_checkbox.isChecked() else None,
            self._date_to_edit.date().toPython() if self._date_to_checkbox.isChecked() else None,
        )
        self._presenter.set_needs_review(self._needs_review_checkbox.isChecked())
        self._refresh()

    def _on_page_size_changed(self):
        self._presenter.set_page_size(self._page_size_combo.currentData())
        self._refresh()

    def _go_previous_page(self):
        if self._presenter.go_previous():
            self._refresh()

    def _go_next_page(self):
        if self._presenter.go_next():
            self._refresh()

    def _refresh(self):
        self._presenter.reload()

        table = self._cycles_table
        table.setRowCount(0)
        for cycle in self._presenter.cycles():
            row = table.rowCount()
            table.insertRow(row)
            self._set_cycle_row(row, cycle)

        self._update_pagination_controls()

    def _update_pagination_controls(self):
        self._pagination_label.setText(self._presenter.pagination_label())
        self._previous_button.setEnabled(self._presenter.can_go_previous())
        self._next_button.setEnabled(self._presenter.can_go_next())

    def _set_cycle_row(self, row, cycle):
        table = self._cycles_table
        for col, text in enumerate(self._presenter.row_cells(cycle)):
            table.setItem(row, col, QTableWidgetItem(text))

        # El número que imprime el informe va en el tooltip y no en una columna
        # propia: solo hace falta para entender por qué un PDF MPI_10_* sale
        # como AUTOCLAVE8, y no merece ensanchar la tabla.
        aviso_codigo = self._presenter.autoclave_tooltip(cycle)
        if aviso_codigo:
            table.item(row, _COL_AUTOCLAVE).setToolTip(aviso_codigo)

        if cycle.needs_review:
            table.item(row, _COL_REVIEW).setToolTip(cycle.review_notes)
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

        self._print_job(cycles).preview(self)

    def _export_selected_to_pdf(self):
        cycles = self._selected_cycles()
        if not cycles:
            push(Module.STERIFLOW, catalog.no_cycles_selected_to_export())
            return

        destino = printing.ask_pdf_path(self, f"{_PRINT_PDF_PREFIX}_{dt.datetime.now():%Y%m%d_%H%M}.pdf")
        if destino is None:
            return

        # Un PDF exportado es un documento que sale de la aplicación: interesa
        # que quede en el log cuándo se generó y dónde, no solo avisar en el
        # momento.
        logger = agent_logger()
        try:
            self._print_job(cycles).export_pdf(destino)
        except OSError as ex:
            announce(logger, catalog.cycles_pdf_save_failed(destino, ex))
            return

        announce(logger, catalog.cycles_pdf_saved(len(cycles), destino))

    def _print_job(self, cycles) -> printing.PrintJob:
        """La tabla de la selección, lista tanto para la impresora como para el PDF."""
        return printing.table_job(
            _PRINT_TITLE,
            _HEADERS,
            [self._presenter.print_cells(cycle) for cycle in cycles],
            subtitle=f"{len(cycles)} ciclo(s)",
            # Los pendientes de revisión salen resaltados en papel igual que en pantalla.
            highlighted=[cycle.needs_review for cycle in cycles],
            aligns=_PRINT_ALIGNS,
        )
