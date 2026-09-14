"""Diálogo de asignación en bloque, desde la pestaña de Ciclos.

Existe porque el selector (`ProgramSelector`) es alto -lista de diez filas más
los campos de consigna manual- y no cabe en la fila de acciones de la tabla,
que era donde vivía el desplegable al que sustituye.

Hace además de confirmación: reasignar reescribe el veredicto calculado de
cada ciclo seleccionado, así que aceptar este diálogo es el acto explícito que
antes pedía un QMessageBox aparte -y aquí se ve al mismo tiempo QUÉ se va a
aplicar y a CUÁNTOS ciclos, que en dos pasos quedaba separado-.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.modules.ferlo.logic.analysis.models import SterilizationProgram
from src.modules.ferlo.logic.analysis.programs import ManualSetpoint
from src.modules.ferlo.ui.data_page.program_selector import ProgramSelector


class AssignProgramDialog(QDialog):
    def __init__(
        self,
        programs: list[SterilizationProgram],
        selected_count: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asignar consigna a la selección")
        self.setModal(True)

        # Sin sugeridos: cada ciclo de la selección tiene su propia consigna
        # medida, así que no hay UNA cercanía que sugerir -sugerir por la del
        # primero sería sugerir a ciegas para el resto-.
        self._selector = ProgramSelector(programs)
        self._selector.selection_changed.connect(self._sync_ok_button)

        cabecera = QLabel(
            f"Se aplicará a <b>{selected_count}</b> ciclo(s) seleccionado(s). "
            "Relee el mensual del archivo y reevalúa cada uno."
        )
        cabecera.setWordWrap(True)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Asignar")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(cabecera)
        layout.addWidget(self._selector)
        layout.addWidget(self._buttons)

        self._sync_ok_button()

    def _sync_ok_button(self) -> None:
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self._selector.has_valid_selection()
        )

    def manual_setpoint(self) -> ManualSetpoint | None:
        return self._selector.manual_setpoint()

    def program_code(self) -> int | None:
        return self._selector.program_code()
