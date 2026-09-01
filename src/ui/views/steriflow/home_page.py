from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.app_button import AppButton


class SteriflowHomePage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_backup_status_group())
        layout.addWidget(self._build_backup_actions_group())
        layout.addStretch()

    def _build_backup_status_group(self):
        group = QGroupBox("Estado del Backup")

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(QLabel("Último backup: -- (hace -- horas)"))
        group_layout.addWidget(QLabel("Próximo backup: -- (dentro de -- horas)"))

        return group

    def _build_backup_actions_group(self):
        group = QGroupBox("Acciones de Backup")

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(AppButton("Ejecutar backup"))
        group_layout.addWidget(AppButton("Detener backup", color="#e20c0c"))
        group_layout.addWidget(AppButton("Abrir carpeta de log"))
        group_layout.addWidget(AppButton("Abrir carpeta local"))
        group_layout.addWidget(AppButton("Abrir carpeta de servidor"))

        return group
