from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.logic.steriflow.controller import SteriflowController
from src.logic.steriflow.logs.logger import Logger
from src.ui.components.app_button import AppButton
from src.ui.folders import open_folder
from src.ui.formatting import format_moment
from src.ui.views.steriflow.backup_runner import BackupRunner

_STATUS_REFRESH_INTERVAL_MS = 60_000
_AGENT_LOG_FILENAME = "steriflow_agent.log"


class SteriflowHomePage(QWidget):
    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._controller = controller

        self._backup_runner = BackupRunner(controller)
        self._backup_runner.started.connect(self._on_backup_started)
        self._backup_runner.finished.connect(self._on_backup_finished)
        self._backup_runner.already_running.connect(self._on_backup_already_running)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(_STATUS_REFRESH_INTERVAL_MS)
        self._status_timer.timeout.connect(self._refresh_status_labels)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_backup_status_group())
        layout.addWidget(self._build_backup_actions_group())
        layout.addWidget(self._build_open_folders_group())
        layout.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_status_labels()
        self._status_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._status_timer.stop()

    def _build_backup_status_group(self):
        group = QGroupBox("Estado del Backup")

        self._last_backup_label = QLabel()
        self._next_backup_label = QLabel()

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._last_backup_label)
        group_layout.addWidget(self._next_backup_label)

        return group

    def _build_backup_actions_group(self):
        group = QGroupBox("Acciones de Backup")

        self._fetch_button = AppButton("Traer de las máquinas")
        self._fetch_button.clicked.connect(self._on_fetch_clicked)

        self._run_button = AppButton("Backup a servidor")
        self._run_button.clicked.connect(self._on_run_clicked)

        self._stop_button = AppButton("Detener backup", color="#e20c0c")
        self._stop_button.clicked.connect(self._on_stop_clicked)

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(self._fetch_button)
        group_layout.addWidget(self._run_button)
        group_layout.addWidget(self._stop_button)

        return group

    def _build_open_folders_group(self):
        group = QGroupBox("Abrir carpetas")

        open_logs_button = AppButton("Abrir carpeta de log")
        open_logs_button.clicked.connect(
            lambda: self._open_folder(self._controller.settings.paths.logs_root, create=True)
        )

        open_local_button = AppButton("Abrir carpeta local")
        open_local_button.clicked.connect(
            lambda: self._open_folder(self._controller.settings.paths.local_root, create=True)
        )

        open_server_button = AppButton("Abrir carpeta de servidor")
        open_server_button.clicked.connect(
            lambda: self._open_folder(self._controller.settings.paths.server_root, create=False)
        )

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(open_logs_button)
        group_layout.addWidget(open_local_button)
        group_layout.addWidget(open_server_button)

        return group

    def _on_fetch_clicked(self):
        self._backup_runner.run(
            source="home_page",
            action=self._controller.backup_service.fetch,
            done_message="Traída desde las máquinas finalizada.",
        )

    def _on_run_clicked(self):
        self._backup_runner.run(
            source="home_page",
            action=self._controller.backup_service.backup,
            done_message="Backup finalizado.",
        )

    def _on_stop_clicked(self):
        self._controller.stop()
        self._refresh_status_labels()

    def _on_backup_started(self):
        self._fetch_button.setEnabled(False)
        self._run_button.setEnabled(False)

    def _on_backup_finished(self, message):
        self._fetch_button.setEnabled(True)
        self._run_button.setEnabled(True)
        self._refresh_status_labels()

    def _on_backup_already_running(self):
        QMessageBox.information(self, "Backup", "Ya hay un backup en curso.")

    def _open_folder(self, path, create):
        logger = Logger(self._controller.settings.paths.logs_root / _AGENT_LOG_FILENAME)
        if not open_folder(path, logger, create=create):
            QMessageBox.warning(self, "Backup", f"No se pudo abrir la carpeta:\n{path}")

    def _refresh_status_labels(self):
        self._last_backup_label.setText(f"Último backup: {format_moment(self._controller.last_backup)}")
        self._next_backup_label.setText(f"Próximo backup: {format_moment(self._controller.next_execution)}")
