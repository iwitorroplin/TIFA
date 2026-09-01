from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton


class SidebarButton(QPushButton):
    def __init__(self, text, icon=None, checkable=True):
        super().__init__(text)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if icon is not None:
            self.setIcon(icon)
            self.setIconSize(QSize(20, 20))

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(
            """
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                text-align: left;
                background-color: transparent;
                color: white;
            }
            QPushButton:hover {
                background-color: #93b6df;
            }
            QPushButton:checked {
                background-color: #2b5c95;
            }
            """
        )
