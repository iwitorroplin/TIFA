from __future__ import annotations

import datetime as dt
import html

from PySide6.QtCore import QDate, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
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
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.shared.db.connection import connect
from src.modules.steriflow.logic.config import load_settings
from src.modules.steriflow.logic.sterilization import repo
from src.modules.steriflow.logic.sterilization import service as sterilization_service
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle
from src.shared.ui.components.app_button import AppButton

_COL_AUTOCLAVE = 0
_COL_STARTED_AT = 1
_COL_PRODUCT = 2
_COL_BATCH = 3
_COL_CYCLE_NUMBER = 4
_COL_DURATION = 5
_COL_TEMP_MEAN = 6
_COL_TEMP_MIN = 7
_COL_TEMP_MAX = 8
_COL_REVIEW = 9

_HEADERS = [
    "Autoclave",
    "Fecha inicio",
    "Producto",
    "Lote",
    "Nº ciclo",
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

_PAGE_SIZES = [20, 50, 100]
_DEFAULT_PAGE_SIZE = 50
# Al escribir en el filtro de producto se espera a que el usuario pare de
# teclear antes de volver a consultar la base de datos, para no lanzar una
# consulta por cada letra.
_FILTER_DEBOUNCE_MS = 300


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    horas, resto = divmod(int(seconds), 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def _format_temp(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"

# _build_print_html y _print_row_html generan el HTML que se pasa a QTextDocument para imprimir. 
# Se hace así en vez de con un QTableWidget porque QTextDocument permite paginar automáticamente, mientras que QTableWidget no.
# Problema_1: si la tabla es muy larga, el QTableWidget no se puede imprimir en varias páginas. Con QTextDocument sí.
# Problema_2: la talba se veria mejor en horizontal
#   añadiremos en la fucnion build la opcion de orientacion.
# asignar por defecto DIN-A4 



def _build_print_html(cycles: list[SterilizationCycle]) -> str:
    filas = "".join(_print_row_html(c) for c in cycles)
    generado = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    return (
        "<h2>Ciclos de esterilización — Steriflow</h2>"
        f"<p>Generado: {generado} &middot; {len(cycles)} ciclo(s)</p>"
        "<table border='1' cellspacing='0' cellpadding='4' width='100%'>"
        "<tr>"
        "<th>Autoclave</th><th>Fecha inicio</th><th>Producto</th><th>Lote</th>"
        "<th>Nº ciclo</th><th>Duración esteril.</th>"
        "<th>T media (°C)</th><th>T mín (°C)</th><th>T máx (°C)</th><th>Revisión</th>"
        "</tr>"
        f"{filas}"
        "</table>"
    )


def _print_row_html(cycle: SterilizationCycle) -> str:
    revision = html.escape(cycle.review_notes) if cycle.needs_review else ""
    return (
        "<tr>"
        f"<td>{cycle.autoclave_code}</td>"
        f"<td>{cycle.started_at.strftime('%d/%m/%Y %H:%M:%S')}</td>"
        f"<td>{html.escape(cycle.product)}</td>"
        f"<td>{html.escape(cycle.batch)}</td>"
        f"<td>{html.escape(cycle.cycle_number)}</td>"
        f"<td>{_format_duration(cycle.sterilization_duration_s)}</td>"
        f"<td>{_format_temp(cycle.sterilization_temp_mean_c)}</td>"
        f"<td>{_format_temp(cycle.sterilization_temp_min_c)}</td>"
        f"<td>{_format_temp(cycle.sterilization_temp_max_c)}</td>"
        f"<td>{revision}</td>"
        "</tr>"
    )


class SteriflowDataPage(QWidget):
    def __init__(self):
        super().__init__()

        self._page_size = _DEFAULT_PAGE_SIZE
        self._current_page = 0
        self._total_count = 0
        self._row_cycles: list[SterilizationCycle] = []

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
        self._reload_cycles()

    def _build_cycles_table(self):
        table = QTableWidget(0, len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(_COL_PRODUCT, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(_COL_BATCH, QHeaderView.ResizeMode.Stretch)
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

        self._date_from_checkbox = QCheckBox("Desde:")
        self._date_from_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_from_edit = QDateEdit(QDate.currentDate())
        self._date_from_edit.setCalendarPopup(True)
        self._date_from_edit.setEnabled(False)
        self._date_from_edit.dateChanged.connect(self._on_filters_changed)

        self._date_to_checkbox = QCheckBox("Hasta:")
        self._date_to_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_to_edit = QDateEdit(QDate.currentDate())
        self._date_to_edit.setCalendarPopup(True)
        self._date_to_edit.setEnabled(False)
        self._date_to_edit.dateChanged.connect(self._on_filters_changed)

        self._needs_review_checkbox = QCheckBox("Solo pendientes de revisión")
        self._needs_review_checkbox.toggled.connect(self._on_filters_changed)

        clear_button = AppButton("Limpiar filtros")
        clear_button.clicked.connect(self._clear_filters)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel("Producto:"))
        row_layout.addWidget(self._product_filter_edit)
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

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(open_pdf_button)
        row_layout.addWidget(print_button)
        row_layout.addStretch()
        return row

    def _build_pagination_row(self):
        self._page_size_combo = QComboBox()
        for size in _PAGE_SIZES:
            self._page_size_combo.addItem(str(size), userData=size)
        self._page_size_combo.setCurrentIndex(_PAGE_SIZES.index(_DEFAULT_PAGE_SIZE))
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
        self._filter_debounce.stop()
        self._product_filter_edit.clear()
        self._date_from_checkbox.setChecked(False)
        self._date_to_checkbox.setChecked(False)
        self._needs_review_checkbox.setChecked(False)
        self._on_filters_changed()

    def _on_filters_changed(self):
        # Un filtro nuevo puede dejar la página actual fuera de rango (menos
        # resultados que antes): se vuelve siempre a la primera página.
        self._current_page = 0
        self._reload_cycles()

    def _on_page_size_changed(self):
        self._page_size = self._page_size_combo.currentData()
        self._current_page = 0
        self._reload_cycles()

    def _go_previous_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._reload_cycles()

    def _go_next_page(self):
        if (self._current_page + 1) * self._page_size < self._total_count:
            self._current_page += 1
            self._reload_cycles()

    def _current_filters(self):
        return {
            "product_query": self._product_filter_edit.text().strip() or None,
            "date_from": self._date_from_edit.date().toPython() if self._date_from_checkbox.isChecked() else None,
            "date_to": self._date_to_edit.date().toPython() if self._date_to_checkbox.isChecked() else None,
            "needs_review": True if self._needs_review_checkbox.isChecked() else None,
        }

    def _reload_cycles(self):
        filters = self._current_filters()

        conn = connect()
        try:
            self._total_count = repo.count_cycles(conn, **filters)
            cycles = repo.list_cycles(
                conn, **filters,
                limit=self._page_size,
                offset=self._current_page * self._page_size,
            )
        finally:
            conn.close()

        self._row_cycles = cycles

        table = self._cycles_table
        table.setRowCount(0)
        for cycle in cycles:
            row = table.rowCount()
            table.insertRow(row)
            self._set_cycle_row(row, cycle)

        self._update_pagination_controls()

    def _update_pagination_controls(self):
        if self._total_count == 0:
            self._pagination_label.setText("Sin ciclos")
        else:
            primero = self._current_page * self._page_size + 1
            ultimo = min(primero + self._page_size - 1, self._total_count)
            self._pagination_label.setText(f"Mostrando {primero}–{ultimo} de {self._total_count}")

        self._previous_button.setEnabled(self._current_page > 0)
        self._next_button.setEnabled((self._current_page + 1) * self._page_size < self._total_count)

    def _set_cycle_row(self, row, cycle):
        table = self._cycles_table

        table.setItem(row, _COL_AUTOCLAVE, QTableWidgetItem(str(cycle.autoclave_code)))
        table.setItem(row, _COL_STARTED_AT, QTableWidgetItem(cycle.started_at.strftime("%d/%m/%Y %H:%M:%S")))
        table.setItem(row, _COL_PRODUCT, QTableWidgetItem(cycle.product))
        table.setItem(row, _COL_BATCH, QTableWidgetItem(cycle.batch))
        table.setItem(row, _COL_CYCLE_NUMBER, QTableWidgetItem(cycle.cycle_number))
        table.setItem(row, _COL_DURATION, QTableWidgetItem(_format_duration(cycle.sterilization_duration_s)))
        table.setItem(row, _COL_TEMP_MEAN, QTableWidgetItem(_format_temp(cycle.sterilization_temp_mean_c)))
        table.setItem(row, _COL_TEMP_MIN, QTableWidgetItem(_format_temp(cycle.sterilization_temp_min_c)))
        table.setItem(row, _COL_TEMP_MAX, QTableWidgetItem(_format_temp(cycle.sterilization_temp_max_c)))

        review_item = QTableWidgetItem("Revisar" if cycle.needs_review else "")
        if cycle.needs_review:
            review_item.setToolTip(cycle.review_notes)
        table.setItem(row, _COL_REVIEW, review_item)

        if cycle.needs_review:
            for col in range(table.columnCount()):
                item = table.item(row, col)
                item.setBackground(_REVIEW_BACKGROUND)
                item.setForeground(_REVIEW_FOREGROUND)

    def _selected_cycles(self) -> list[SterilizationCycle]:
        filas = sorted({index.row() for index in self._cycles_table.selectionModel().selectedRows()})
        return [self._row_cycles[fila] for fila in filas if fila < len(self._row_cycles)]

    def _on_row_double_clicked(self, row, column):
        if 0 <= row < len(self._row_cycles):
            self._open_pdfs([self._row_cycles[row]])

    def _open_selected_pdfs(self):
        cycles = self._selected_cycles()
        if not cycles:
            QMessageBox.information(self, "Abrir PDF", "Selecciona al menos un ciclo.")
            return
        self._open_pdfs(cycles)

    def _open_pdfs(self, cycles: list[SterilizationCycle]):
        settings = load_settings()
        fallos = []
        for cycle in cycles:
            ruta = sterilization_service.find_pdf(settings, cycle.source_filename)
            if ruta is None:
                fallos.append(f"{cycle.source_filename}: no se encuentra el fichero")
            elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta))):
                fallos.append(f"{cycle.source_filename}: el sistema no pudo abrirlo")

        if fallos:
            QMessageBox.warning(self, "Abrir PDF", "No se pudieron abrir:\n" + "\n".join(fallos))

    def _print_selected(self):
        cycles = self._selected_cycles()
        if not cycles:
            QMessageBox.information(self, "Imprimir", "Selecciona al menos un ciclo para imprimir.")
            return

        document = QTextDocument()
        document.setHtml(_build_print_html(cycles))

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintPreviewDialog(printer, self)
        dialog.paintRequested.connect(lambda p: document.print_(p))
        dialog.exec()
