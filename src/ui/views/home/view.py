from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.ui.assets import UI_ICON


class HomeView(QWidget):
    def __init__(self):
        super().__init__()

        title = QLabel("7th Heaven")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        image = QSvgWidget(str(UI_ICON))
        image.setFixedSize(160, 160)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
