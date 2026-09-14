from PySide6.QtCore import QDate, QTimer
from PySide6.QtWidgets import QCheckBox, QDateEdit, QHBoxLayout, QLabel, QLineEdit, QWidget

from src.shared.ui.components.app_button import AppButton
from src.shared.ui.components.multi_select_combo_box import MultiSelectComboBox

# Al escribir en el filtro de producto se espera a que el usuario pare de
# teclear antes de volver a consultar la base de datos, para no lanzar una
# consulta por cada letra.
_FILTER_DEBOUNCE_MS = 300


class FiltersRow(QWidget):
    """Fila de filtros: producto, autoclave, dirección/rango de fechas y
    pendientes de revisión. Llama a `on_change` (debounced en el texto de
    producto) cada vez que cambia algo; el view model se consulta a través de
    `view_model.autoclaves()` para cargar el combo de autoclaves."""

    def __init__(self, view_model, on_change, parent=None):
        super().__init__(parent)
        self._view_model = view_model
        self._on_change = on_change

        self._filter_debounce = QTimer(self)
        self._filter_debounce.setSingleShot(True)
        self._filter_debounce.setInterval(_FILTER_DEBOUNCE_MS)
        self._filter_debounce.timeout.connect(self._on_change)

        self._product_filter_edit = QLineEdit()
        self._product_filter_edit.setPlaceholderText("Buscar producto...")
        self._product_filter_edit.textChanged.connect(self._filter_debounce.start)

        self._autoclave_combo = MultiSelectComboBox()
        self._autoclave_combo.add_items(self._view_model.autoclaves(), checked=True)
        self._autoclave_combo.selection_changed.connect(self._on_change)

        self._date_direction_checkbox = QCheckBox("Más antiguos primero")
        self._date_direction_checkbox.toggled.connect(self._on_change)

        self._date_from_checkbox = QCheckBox("Desde:")
        self._date_from_edit = QDateEdit(QDate.currentDate())
        self._date_from_edit.setCalendarPopup(True)
        self._date_from_edit.setEnabled(False)
        self._date_from_edit.dateChanged.connect(self._on_change)

        self._date_to_checkbox = QCheckBox("Hasta:")
        self._date_to_edit = QDateEdit(QDate.currentDate())
        self._date_to_edit.setCalendarPopup(True)
        self._date_to_edit.setEnabled(False)
        self._date_to_edit.dateChanged.connect(self._on_change)

        # Por defecto se filtra desde hoy: abrir la pestaña y ver todo el
        # histórico de golpe es tanto más lento como menos útil que partir del
        # día en curso. Se marca ANTES de conectar `toggled` -si no, dispara
        # `_on_date_filter_toggled`/`on_change` en plena construcción, antes
        # de que la página orquestadora termine de montar tabla y paginación-.
        # El enable visual se aplica a mano; el primer refresco real lo hace
        # el `showEvent` de la página.
        self._date_from_checkbox.setChecked(True)
        self._date_from_edit.setEnabled(True)

        self._date_from_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_to_checkbox.toggled.connect(self._on_date_filter_toggled)

        self._needs_review_checkbox = QCheckBox("Solo pendientes de revisión")
        self._needs_review_checkbox.toggled.connect(self._on_change)

        clear_button = AppButton("Limpiar filtros")
        clear_button.clicked.connect(self._clear_filters)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Producto:"))
        layout.addWidget(self._product_filter_edit)
        layout.addWidget(QLabel("Autoclave:"))
        layout.addWidget(self._autoclave_combo)
        layout.addWidget(self._date_direction_checkbox)
        layout.addWidget(self._date_from_checkbox)
        layout.addWidget(self._date_from_edit)
        layout.addWidget(self._date_to_checkbox)
        layout.addWidget(self._date_to_edit)
        layout.addWidget(self._needs_review_checkbox)
        layout.addWidget(clear_button)
        layout.addStretch()

    def _on_date_filter_toggled(self):
        self._date_from_edit.setEnabled(self._date_from_checkbox.isChecked())
        self._date_to_edit.setEnabled(self._date_to_checkbox.isChecked())
        self._on_change()

    def _clear_filters(self):
        # Los filtros por defecto son fecha (desde hoy) y todas las
        # autoclaves, no "sin filtros": es la vista que de verdad se usa al
        # entrar. El agrupado por autoclave ascendente es siempre el mismo
        # (no depende de ningún filtro), así que aquí solo hace falta
        # resetear la dirección dentro de cada grupo.
        self._filter_debounce.stop()
        self._product_filter_edit.clear()
        self._autoclave_combo.select_all()
        self._date_direction_checkbox.setChecked(False)
        self._date_from_edit.setDate(QDate.currentDate())
        self._date_to_checkbox.setChecked(False)
        self._needs_review_checkbox.setChecked(False)
        if self._date_from_checkbox.isChecked():
            # Ya estaba marcado: forzar el recálculo, que si no sólo lo
            # dispara el toggled de arriba.
            self._on_change()
        else:
            self._date_from_checkbox.setChecked(True)

    def apply_to_view_model(self):
        """Vuelca el estado actual de los filtros al view model. Se llama
        antes de cada refresco (`on_change` ya lo dispara), nunca al revés:
        los widgets son la fuente de verdad de lo que el usuario ve marcado."""
        self._view_model.set_product_query(self._product_filter_edit.text().strip())
        self._view_model.set_autoclave_codes(
            None if self._autoclave_combo.is_all_selected() else self._autoclave_combo.selected_values()
        )
        self._view_model.set_started_at_ascending(self._date_direction_checkbox.isChecked())
        self._view_model.set_date_range(
            self._date_from_edit.date().toPython() if self._date_from_checkbox.isChecked() else None,
            self._date_to_edit.date().toPython() if self._date_to_checkbox.isChecked() else None,
        )
        self._view_model.set_needs_review(self._needs_review_checkbox.isChecked())
