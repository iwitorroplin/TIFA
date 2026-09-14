from PySide6.QtCore import QDate, QTimer
from PySide6.QtWidgets import QCheckBox, QDateEdit, QHBoxLayout, QLabel, QWidget

from src.shared.ui.components.app_button import AppButton
from src.shared.ui.components.multi_select_combo_box import MultiSelectComboBox

_FILTER_DEBOUNCE_MS = 300


class FiltersRow(QWidget):
    """Fila de filtros: máquina, rango de fechas y pendientes de revisión."""

    def __init__(self, controller, view_model, on_change, parent=None):
        super().__init__(parent)
        self._view_model = view_model
        self._on_change = on_change

        self._filter_debounce = QTimer(self)
        self._filter_debounce.setSingleShot(True)
        self._filter_debounce.setInterval(_FILTER_DEBOUNCE_MS)
        self._filter_debounce.timeout.connect(self._on_change)

        self._machine_combo = MultiSelectComboBox()
        self._machine_combo.add_items(((m, m) for m in controller.machines), checked=True)
        self._machine_combo.selection_changed.connect(self._on_change)

        self._date_from_checkbox = QCheckBox("Desde:")
        self._date_from_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_from_edit = QDateEdit(QDate.currentDate())
        self._date_from_edit.setCalendarPopup(True)
        self._date_from_edit.setEnabled(False)
        self._date_from_edit.dateChanged.connect(self._on_change)

        self._date_to_checkbox = QCheckBox("Hasta:")
        self._date_to_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_to_edit = QDateEdit(QDate.currentDate())
        self._date_to_edit.setCalendarPopup(True)
        self._date_to_edit.setEnabled(False)
        self._date_to_edit.dateChanged.connect(self._on_change)

        self._needs_review_checkbox = QCheckBox("Solo pendientes de revisión")
        self._needs_review_checkbox.toggled.connect(self._on_change)

        clear_button = AppButton("Limpiar filtros")
        clear_button.clicked.connect(self._clear_filters)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Máquina:"))
        layout.addWidget(self._machine_combo)
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
        self._filter_debounce.stop()
        self._machine_combo.select_all()
        self._date_from_checkbox.setChecked(False)
        self._date_to_checkbox.setChecked(False)
        self._needs_review_checkbox.setChecked(False)
        self._view_model.clear_filters()
        self._on_change()

    def apply_to_view_model(self):
        self._view_model.set_machines(
            None if self._machine_combo.is_all_selected() else self._machine_combo.selected_values()
        )
        self._view_model.set_date_range(
            self._date_from_edit.date().toPython() if self._date_from_checkbox.isChecked() else None,
            self._date_to_edit.date().toPython() if self._date_to_checkbox.isChecked() else None,
        )
        self._view_model.set_needs_review(self._needs_review_checkbox.isChecked())
