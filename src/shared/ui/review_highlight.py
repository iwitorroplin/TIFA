"""Cómo se marca en una tabla una fila pendiente de revisión, igual en todos
los módulos (hoy las tablas de ciclos de Steriflow y de Ferlo)."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget

# Fondo y letra se fijan los dos explícitamente: la app puede correr con tema
# claro u oscuro (letra blanca por defecto en oscuro), y un fondo claro con
# letra heredada blanca queda ilegible. Fijando ambos hay contraste siempre.
REVIEW_BACKGROUND = QColor(255, 244, 200)
REVIEW_FOREGROUND = QColor(90, 60, 0)


def paint_review_row(table: QTableWidget, row: int) -> None:
    """Resalta todas las celdas de `row`. Las celdas ya tienen que existir."""
    for col in range(table.columnCount()):
        item = table.item(row, col)
        item.setBackground(REVIEW_BACKGROUND)
        item.setForeground(REVIEW_FOREGROUND)
