"""Detalle de un ciclo (Fase 4, D9: pyqtgraph -decisión tomada, no la
recomendada- para la curva). Único sitio de la Fase 4 donde una persona
puede cambiar el estado de un ciclo: asignar/retirar programa y fijar el
veredicto manual. Las dos escrituras son actos explícitos -nunca los hace
una reimportación, ver los invariantes de la Fase 0.
"""

from __future__ import annotations

import math

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.analysis import programs as programs_service
from src.modules.ferlo.logic.analysis.models import ManualVerdict
from src.modules.ferlo.logic.analysis.queries import cycle_detail
from src.modules.ferlo.logic.controller import FerloController
from src.modules.ferlo.messages import catalog
from src.shared.messages.notice import push
from src.shared.messages.types import Module
from src.modules.ferlo.logic.analysis.programs import MANUAL_PROGRAM_CODE
from src.modules.ferlo.ui.data_page.program_selector import ProgramSelector
from src.shared.ui.components.app_button import AppSaveButton

_SEVERITY_COLORS = {"info": "#4d88cb", "review": "#c98a00", "error": "#e20c0c"}


class FerloDetailDialog(QDialog):
    def __init__(self, controller: FerloController, cycle_id: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._cycle_id = cycle_id

        self.setWindowTitle("Detalle del ciclo")
        self.resize(920, 700)

        self._reload()
        self._build_ui()

    def _reload(self) -> None:
        self._cycle, self._samples, self._incidents = cycle_detail(self._cycle_id)
        self._programs = self._controller.list_programs(include_inactive=True)

    def _build_ui(self) -> None:
        cycle = self._cycle
        layout = QVBoxLayout(self)

        if cycle is None:
            layout.addWidget(QLabel("Este ciclo ya no existe -puede que se haya reanalizado y "
                                     "haya cambiado de identidad."))
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(self.reject)
            buttons.accepted.connect(self.accept)
            layout.addWidget(buttons)
            return

        # Dos columnas: a la izquierda lo que se lee y se decide (datos del
        # ciclo, programa, veredicto, incidencias) y a la derecha la curva, que
        # es lo que necesita ancho. Apilado en vertical, como estaba, la curva
        # quedaba estrujada entre la cabecera y tres grupos.
        columnas = QHBoxLayout()
        columnas.addWidget(self._build_left_column(cycle), 1)
        columnas.addWidget(self._build_plot(cycle), 2)
        layout.addLayout(columnas)

        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.accept)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

    def _build_left_column(self, cycle) -> QWidget:
        contenido = QWidget()
        columna = QVBoxLayout(contenido)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.addWidget(self._build_header(cycle))
        columna.addWidget(self._build_assignment_group(cycle))
        columna.addWidget(self._build_review_group(cycle))
        columna.addWidget(self._build_incidents_group(), 1)

        # Dentro de un scroll: con muchas incidencias, la tabla aplastaba al
        # resto de la columna en pantallas bajas.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(contenido)
        return scroll

    def _build_header(self, cycle) -> QWidget:
        programa = f"{cycle.program_code:02d} · {cycle.program_name}" if cycle.program_code else "sin asignar"
        # Las dos duraciones con su nombre: la del ciclo entero y la de la
        # meseta, que son muy distintas (96,8 min frente a 73,6 en un ciclo
        # real) y antes salía solo la primera, a secas, como "min".
        esterilizacion = cycle.sterilization_duration_min
        duraciones = f"ciclo {cycle.duration_min:.1f} min"
        if esterilizacion is not None:
            duraciones += f" · esterilización {esterilizacion:.1f} min"
        texto = (
            f"<b>{cycle.machine}</b> · {cycle.started_at:%d/%m/%Y %H:%M:%S} → {cycle.ended_at:%H:%M:%S}"
            f" · {duraciones} · programa {programa}"
            f" · consigna medida {cycle.measured_setpoint_c:.1f} °C"
            f" · estado <b>{catalog.status_label(cycle.status)}</b>"
        )
        label = QLabel(texto)
        label.setWordWrap(True)
        return label

    def _build_plot(self, cycle) -> QWidget:
        plot = pg.PlotWidget()
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.setLabel("bottom", "Tiempo desde el inicio del ciclo", units="s")
        plot.setLabel("left", "Temperatura", units="°C")

        if not self._samples:
            return plot

        t0 = self._samples[0][0]
        xs = [(ts - t0).total_seconds() for ts, _ in self._samples]
        ys = [temp if temp is not None else math.nan for _, temp in self._samples]
        plot.plot(xs, ys, pen=pg.mkPen("#B44A1E", width=2), connect="finite")

        if cycle.evaluation_setpoint_c:
            plot.addLine(
                y=cycle.evaluation_setpoint_c,
                pen=pg.mkPen("#1D5C77", width=1, style=Qt.PenStyle.DashLine),
                label=f"consigna {cycle.evaluation_setpoint_c:.1f} °C",
            )
            tolerancia = float(
                self._controller.settings.sterilization_phase["sterilization_tolerance_c"]
            )
            plot.addLine(
                y=cycle.evaluation_setpoint_c - tolerancia,
                pen=pg.mkPen("#1D5C77", width=1, style=Qt.PenStyle.DotLine),
                label="banda",
            )

        for incidencia in self._incidents:
            if incidencia.ts is None:
                continue
            x = (incidencia.ts - t0).total_seconds()
            color = _SEVERITY_COLORS.get(incidencia.severity.value, "#888888")
            plot.addLine(x=x, pen=pg.mkPen(color, width=1, style=Qt.PenStyle.DashLine))

        return plot

    def _build_incidents_group(self) -> QWidget:
        group = QGroupBox(f"Incidencias ({len(self._incidents)})")
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Instante", "Severidad", "Código", "Mensaje"])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for incidencia in self._incidents:
            row = table.rowCount()
            table.insertRow(row)
            momento = incidencia.ts.strftime("%d/%m %H:%M:%S") if incidencia.ts else "—"
            table.setItem(row, 0, QTableWidgetItem(momento))
            table.setItem(row, 1, QTableWidgetItem(incidencia.severity.value))
            table.setItem(row, 2, QTableWidgetItem(incidencia.code.value))
            table.setItem(row, 3, QTableWidgetItem(incidencia.message))

        layout = QVBoxLayout(group)
        layout.addWidget(table)
        return group

    def _build_assignment_group(self, cycle) -> QWidget:
        group = QGroupBox("Programa")

        sugeridos = programs_service.suggest_programs(self._programs, cycle.measured_setpoint_c)
        self._program_selector = ProgramSelector(self._programs, suggested=sugeridos)
        self._program_selector.select_program(cycle.program_code)
        if cycle.program_code == MANUAL_PROGRAM_CODE:
            # Consigna manual ya asignada: los valores son los del ciclo, no
            # los de la fila 0 -que no los guarda, ver `manual_program`-.
            self._program_selector.set_manual_setpoint(
                cycle.target_temperature_c or 0.0, cycle.target_time_min or 0.0
            )

        self._assign_button = QPushButton("Asignar")
        self._assign_button.setToolTip(
            "Relee el mensual del archivo y reevalúa este ciclo con la consigna elegida."
        )
        self._assign_button.clicked.connect(self._on_assign_clicked)
        self._program_selector.selection_changed.connect(self._sync_assign_button)

        boton_row = QHBoxLayout()
        boton_row.addStretch()
        boton_row.addWidget(self._assign_button)

        layout = QVBoxLayout(group)
        layout.addWidget(self._program_selector)
        layout.addLayout(boton_row)
        if sugeridos:
            hint = QLabel("★ = sugerido por cercanía a la consigna medida (no elige, solo sugiere).")
            hint.setWordWrap(True)
            layout.addWidget(hint)
        self._sync_assign_button()
        return group

    def _sync_assign_button(self) -> None:
        self._assign_button.setEnabled(self._program_selector.has_valid_selection())

    def _build_review_group(self, cycle) -> QWidget:
        group = QGroupBox("Revisión manual")

        self._verdict_combo = QComboBox()
        for verdict in ManualVerdict:
            # userData guarda `.value` (str) y no el enum: al ser
            # `ManualVerdict(str, Enum)`, Qt lo cruza a través de QVariant
            # como texto plano y lo devuelve como `str` normal, no como el
            # enum -perdería `.value` al leerlo de vuelta en
            # `_on_save_review_clicked`-.
            self._verdict_combo.addItem(catalog.verdict_label(verdict), userData=verdict.value)
        index = self._verdict_combo.findData(cycle.manual_verdict)
        if index >= 0:
            self._verdict_combo.setCurrentIndex(index)

        self._notes_edit = QPlainTextEdit(cycle.review_notes or "")
        self._notes_edit.setPlaceholderText("Notas de revisión (opcional)...")
        self._notes_edit.setFixedHeight(70)

        save_button = AppSaveButton("Guardar revisión")
        save_button.clicked.connect(self._on_save_review_clicked)

        row = QHBoxLayout()
        row.addWidget(QLabel("Veredicto:"))
        row.addWidget(self._verdict_combo)
        row.addWidget(save_button)
        row.addStretch()

        layout = QVBoxLayout(group)
        layout.addLayout(row)
        layout.addWidget(self._notes_edit)
        return group

    def _on_assign_clicked(self) -> None:
        cycle = self._cycle
        manual = self._program_selector.manual_setpoint()
        program_code = MANUAL_PROGRAM_CODE if manual else self._program_selector.program_code()

        resultado = self._controller.reassign_program(
            cycle.machine, cycle.started_at, program_code, manual
        )
        if resultado is None:
            push(Module.FERLO, catalog.assignment_failed())
            return

        if manual is not None:
            push(Module.FERLO, catalog.manual_setpoint_assigned(
                cycle.machine, manual.target_temperature_c, manual.target_time_min
            ))
        elif program_code is None:
            push(Module.FERLO, catalog.program_unassigned(cycle.machine))
        else:
            push(Module.FERLO, catalog.program_assigned(cycle.machine, program_code))

        self._reload()
        self._rebuild()

    def _on_save_review_clicked(self) -> None:
        verdict = ManualVerdict(self._verdict_combo.currentData())
        notes = self._notes_edit.toPlainText().strip() or None
        self._controller.set_manual_verdict(self._cycle_id, verdict, notes)
        push(Module.FERLO, catalog.verdict_saved(self._cycle.machine))
        self._reload()

    def _rebuild(self) -> None:
        # El programa asignado cambia la consigna de evaluación y por tanto
        # la banda dibujada en la curva: se reconstruye la ventana entera en
        # vez de intentar actualizar cada widget por separado. Reparentar el
        # layout actual a un QWidget desechable es el modismo de Qt para
        # quitarle a `self` un layout junto con todos sus widgets hijos, así
        # que `_build_ui()` puede volver a poner uno nuevo desde cero.
        old_layout = self.layout()
        if old_layout is not None:
            QWidget().setLayout(old_layout)
        self._build_ui()
