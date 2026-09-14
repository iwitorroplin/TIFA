from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from src.shared.ui.components.app_button import AppButton
from src.shared.ui.paged_view_model import DEFAULT_PAGE_SIZE, PagedViewModel

_PAGE_SIZES = [20, 50, 100]


class PaginationRow(QWidget):
    """Fila de paginación: tamaño de página, anterior/siguiente y la
    etiqueta con el rango mostrado.

    Mueve la página en `view_model` y avisa con `on_changed` para que la
    página orquestadora recargue y repinte; si el movimiento no es posible
    (ya en el borde) no avisa, así no se relanza una consulta en balde."""

    def __init__(self, view_model: PagedViewModel, on_changed: Callable[[], None], parent=None):
        super().__init__(parent)
        self._view_model = view_model
        self._on_changed = on_changed

        self._page_size_combo = QComboBox()
        for size in _PAGE_SIZES:
            self._page_size_combo.addItem(str(size), userData=size)
        self._page_size_combo.setCurrentIndex(_PAGE_SIZES.index(DEFAULT_PAGE_SIZE))
        self._page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)

        self._previous_button = AppButton("< Anterior")
        self._previous_button.clicked.connect(self._on_previous_clicked)

        self._next_button = AppButton("Siguiente >")
        self._next_button.clicked.connect(self._on_next_clicked)

        self._pagination_label = QLabel()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Mostrar:"))
        layout.addWidget(self._page_size_combo)
        layout.addStretch()
        layout.addWidget(self._pagination_label)
        layout.addWidget(self._previous_button)
        layout.addWidget(self._next_button)

    def _on_page_size_changed(self):
        self._view_model.set_page_size(self._page_size_combo.currentData())
        self._on_changed()

    def _on_previous_clicked(self):
        if self._view_model.go_previous():
            self._on_changed()

    def _on_next_clicked(self):
        if self._view_model.go_next():
            self._on_changed()

    def repaint(self):
        self._pagination_label.setText(self._view_model.pagination_label())
        self._previous_button.setEnabled(self._view_model.can_go_previous())
        self._next_button.setEnabled(self._view_model.can_go_next())
