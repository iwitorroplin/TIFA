from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton


class AppButton(QPushButton):
    def __init__(self, text, color="#4d88cb"):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        base = QColor(color)
        default = base.name()
        hover = base.lighter(130).name()
        pressed = base.darker(120).name()

        self.setStyleSheet(
            f"""
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                background-color: {default};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
            """
        )
