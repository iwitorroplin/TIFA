from PySide6.QtWidgets import QCheckBox, QVBoxLayout, QWidget


class ConfigView(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.addWidget(QCheckBox("Iniciar TIFA al iniciar sesión de Windows"))
        layout.addStretch()
