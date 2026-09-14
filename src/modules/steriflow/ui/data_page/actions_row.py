from PySide6.QtWidgets import QHBoxLayout, QWidget

from src.shared.ui.components.app_button import AppButton


class ActionsRow(QWidget):
    """Fila de acciones sobre la selección: abrir PDF, imprimir, exportar."""

    def __init__(self, on_open_pdfs, on_print, on_export_pdf, parent=None):
        super().__init__(parent)

        open_pdf_button = AppButton("Abrir PDF")
        open_pdf_button.clicked.connect(on_open_pdfs)

        print_button = AppButton("Imprimir selección")
        print_button.clicked.connect(on_print)

        export_pdf_button = AppButton("Guardar tabla en PDF")
        export_pdf_button.clicked.connect(on_export_pdf)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(open_pdf_button)
        layout.addWidget(print_button)
        layout.addWidget(export_pdf_button)
        layout.addStretch()
