from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from src.modules.ferlo.ui.data_page.data_presenter import DEFAULT_PAGE_SIZE
from src.shared.ui.components.app_button import AppButton

_PAGE_SIZES = [20, 50, 100]


class PaginationRow(QWidget):
    """Fila de paginación: tamaño de página, anterior/siguiente y la
    etiqueta con el rango mostrado."""

    def __init__(self, presenter, on_page_size_changed, on_previous, on_next, parent=None):
        super().__init__(parent)
        self._presenter = presenter

        self._page_size_combo = QComboBox()
        for size in _PAGE_SIZES:
            self._page_size_combo.addItem(str(size), userData=size)
        self._page_size_combo.setCurrentIndex(_PAGE_SIZES.index(DEFAULT_PAGE_SIZE))
        self._page_size_combo.currentIndexChanged.connect(
            lambda: on_page_size_changed(self._page_size_combo.currentData())
        )

        self._previous_button = AppButton("< Anterior")
        self._previous_button.clicked.connect(on_previous)

        self._next_button = AppButton("Siguiente >")
        self._next_button.clicked.connect(on_next)

        self._pagination_label = QLabel()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Mostrar:"))
        layout.addWidget(self._page_size_combo)
        layout.addStretch()
        layout.addWidget(self._pagination_label)
        layout.addWidget(self._previous_button)
        layout.addWidget(self._next_button)

    def repaint(self):
        self._pagination_label.setText(self._presenter.pagination_label())
        self._previous_button.setEnabled(self._presenter.can_go_previous())
        self._next_button.setEnabled(self._presenter.can_go_next())
