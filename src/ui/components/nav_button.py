from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton


class NavButton(QPushButton):
    def __init__(
            self,
            text, 
            icon=None, 
            color="#005eca",
            checkable=True):

        super().__init__(text)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if icon is not None:
            self.setIcon(QIcon(str(icon)))
            self.setIconSize(QSize(20, 20))

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        base = QColor(color)
        default = base.name()
        hover = base.lighter(140).name()
        checked = base.darker(140).name()

        self.setStyleSheet(
            f"""
            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                text-align: left;
                background-color: {default};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:checked {{
                background-color: {checked};
            }}
            """
        )
