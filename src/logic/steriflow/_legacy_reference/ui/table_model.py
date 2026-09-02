"""Modelo de tabla de ciclos Steriflow.

Misma tecnica que el modelo de Ferlo: `EditRole` devuelve el valor nativo
(int/float/timestamp) que usa el orden y `DisplayRole` solo formatea, para que
ordenar por "duracion" no ponga "10,0 min" antes que "9,0 min".

Las columnas son las de la FASE 3, la de esterilizacion (ver
`models.STERILIZATION_PHASE_NUMBER`). Las otras cinco fases estan guardadas y
mostrarlas es cuestion de anadir columnas aqui, sin reimportar nada.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from ...core.formatting import fmt_num, fmt_ts
from ..repo import SteriflowCycleRow

COLUMNAS = (
    "id", "autoclave", "inicio ciclo", "nº ciclo", "producto",
    "inicio esteril.", "fin esteril.", "duración",
    "media °C", "mín °C", "máx °C", "T fin °C", "fichero",
)

(_COL_ID, _COL_AUTOCLAVE, _COL_INICIO_CICLO, _COL_NUM_CICLO, _COL_PRODUCTO,
 _COL_INICIO, _COL_FIN, _COL_DURACION,
 _COL_MEDIA, _COL_MIN, _COL_MAX, _COL_T_FIN, _COL_FICHERO) = range(len(COLUMNAS))

COL_ID = _COL_ID  # publico: la vista lee de aqui el id de la fila seleccionada

_COLUMNAS_NUMERICAS = {
    _COL_ID, _COL_DURACION, _COL_MEDIA, _COL_MIN, _COL_MAX, _COL_T_FIN,
}


def _num_o_menos_uno(valor: float | None) -> float:
    """-1.0 para 'sin dato': ordena antes que cualquier valor real sin
    necesitar una comparacion especial."""
    return valor if valor is not None else -1.0


class SteriflowTableModel(QAbstractTableModel):
    """Vista de solo lectura sobre una lista de `SteriflowCycleRow`."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cycles: list[SteriflowCycleRow] = []
        self._autoclave_names: dict[int, str] = {}

    def set_cycles(
        self,
        cycles: list[SteriflowCycleRow],
        *,
        autoclave_names: dict[int, str] | None = None,
    ) -> None:
        self.beginResetModel()
        self._cycles = cycles
        if autoclave_names is not None:
            self._autoclave_names = autoclave_names
        self.endResetModel()

    def cycle_at(self, row: int) -> SteriflowCycleRow | None:
        return self._cycles[row] if 0 <= row < len(self._cycles) else None

    # ---------------------------------------------------------------- Qt API

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._cycles)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNAS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNAS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        fila = self._cycles[index.row()]
        col = index.column()

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self._valor(fila, col, edit=role == Qt.ItemDataRole.EditRole)
        if role == Qt.ItemDataRole.TextAlignmentRole and col in _COLUMNAS_NUMERICAS:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            return fila.batch or None
        return None

    def _valor(self, fila: SteriflowCycleRow, col: int, *, edit: bool):
        fase = fila.sterilization

        if col == _COL_ID:
            return fila.id
        if col == _COL_AUTOCLAVE:
            return self._autoclave_names.get(fila.autoclave_code, str(fila.autoclave_code))
        if col == _COL_INICIO_CICLO:
            return fila.started_at.timestamp() if edit else fmt_ts(fila.started_at)
        if col == _COL_NUM_CICLO:
            return fila.cycle_number or "-"
        if col == _COL_PRODUCTO:
            return fila.product or "-"
        if col == _COL_FICHERO:
            return fila.source_filename

        # A partir de aqui todo sale de la fase 3. Un ciclo sin ella -informe
        # truncado o de otra receta- se muestra con guiones en vez de
        # desaparecer del listado: que falte es justo lo que hay que ver.
        if fase is None:
            return -1.0 if edit and col in _COLUMNAS_NUMERICAS else "-"

        if col == _COL_INICIO:
            return fase.start_ts.timestamp() if edit else fmt_ts(fase.start_ts)
        if col == _COL_FIN:
            return fase.end_ts.timestamp() if edit else fmt_ts(fase.end_ts)
        if col == _COL_DURACION:
            return fase.duration_min if edit else fmt_num(fase.duration_min, "min", 2)
        if col == _COL_MEDIA:
            return (_num_o_menos_uno(fase.temperature_mean_c) if edit
                    else fmt_num(fase.temperature_mean_c, "", 2))
        if col == _COL_MIN:
            return (_num_o_menos_uno(fase.temperature_min_c) if edit
                    else fmt_num(fase.temperature_min_c, "", 2))
        if col == _COL_MAX:
            return (_num_o_menos_uno(fase.temperature_max_c) if edit
                    else fmt_num(fase.temperature_max_c, "", 2))
        if col == _COL_T_FIN:
            return (_num_o_menos_uno(fase.temperature_end_c) if edit
                    else fmt_num(fase.temperature_end_c, "", 2))
        return None
