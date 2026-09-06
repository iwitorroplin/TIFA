from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.modules.steriflow.logic.controller import AGENT_LOG_FILENAME, SteriflowController
from src.shared.logs.logger import Logger
from src.modules.steriflow.logic.network import MachineStatus
from src.shared.ui.components.app_button import (
    AppButton,
    AppFolderButton,
    AppStartButton,
)

from src.shared.ui.formatting import format_moment
from src.shared.messages.manager import manager
from src.shared.messages.types import MessageType, Module
from src.modules.steriflow.ui.backup_runner import BackupRunner
from src.modules.steriflow.ui.status_checker import AutoclaveStatusChecker



_STATUS_REFRESH_INTERVAL_MS = 60_000


class SteriflowHomePage(QWidget):
    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._controller = controller

        # Solo estado de los botones: lo que se le dice al usuario sobre el
        # backup lo dice el propio log de la acción (ver BackupRunner).
        self._backup_runner = BackupRunner(controller)
        self._backup_runner.started.connect(self._on_backup_started)
        self._backup_runner.finished.connect(self._on_backup_finished)

        self._connectivity_checker = AutoclaveStatusChecker(self)
        self._connectivity_checker.checked.connect(self._on_connectivity_checked)
        self._pending_connectivity_checks: dict[str, MachineStatus | None] = {}

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

        self._auto_mode_checkbox = QCheckBox("Backups automáticos activados")
        self._auto_mode_checkbox.setChecked(self._controller.auto_enabled)
        # `clicked` y no `toggled`: toggled también salta cuando es la propia
        # app la que marca la casilla en _refresh_status_labels, y entonces se
        # anunciaría un cambio que el usuario no ha hecho.
        self._auto_mode_checkbox.clicked.connect(self._on_auto_mode_toggled)

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(self._last_backup_label)
        group_layout.addWidget(self._next_backup_label)
        group_layout.addWidget(self._auto_mode_checkbox)

        return group

    def _build_backup_actions_group(self):
        group = QGroupBox("Acciones de Backup")

        self._check_button = AppButton("Comprobar conexión")
        self._check_button.clicked.connect(self._on_check_clicked)

        self._fetch_button = AppStartButton("Importar (máquinas a local)")
        self._fetch_button.clicked.connect(self._on_fetch_clicked)

        self._run_button = AppStartButton("Exportar (local a servidor)")
        self._run_button.clicked.connect(self._on_run_clicked)

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(self._check_button)
        group_layout.addWidget(self._fetch_button)
        group_layout.addWidget(self._run_button)
        group_layout.addStretch()

        return group

    def _build_open_folders_group(self):
        group = QGroupBox("Abrir carpetas")

        logger = self._agent_logger()
        paths = self._controller.settings.paths

        open_logs_button = AppFolderButton("Abrir logs", paths.logs_root, logger, create=True)
        open_local_button = AppFolderButton("Abrir Local", paths.local_root, logger, create=True)
        open_server_button = AppFolderButton("Abrir Servidor", paths.server_root, logger, create=False)

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(open_logs_button)
        group_layout.addWidget(open_local_button)
        group_layout.addWidget(open_server_button)
        group_layout.addStretch()

        return group

    def _agent_logger(self) -> Logger:
        """Nuevo en cada uso, no guardado: la carpeta de logs puede cambiar en
        la pestaña de configuración mientras la app sigue abierta."""
        return Logger(
            self._controller.settings.paths.logs_root / AGENT_LOG_FILENAME, Module.STERIFLOW
        )

    def _on_check_clicked(self):
        autoclaves = [a for a in self._controller.settings.autoclaves if a.active]
        if not autoclaves:
            manager.push(Module.STERIFLOW, MessageType.WARNING, "No hay autoclaves activas configuradas.")
            return

        self._check_button.setEnabled(False)
        self._pending_connectivity_checks = {autoclave.name: None for autoclave in autoclaves}
        self._connectivity_checker.check([(a.name, a.ip) for a in autoclaves])

    def _on_connectivity_checked(self, name, status: MachineStatus):
        if name not in self._pending_connectivity_checks:
            return
        self._pending_connectivity_checks[name] = status
        if any(value is None for value in self._pending_connectivity_checks.values()):
            return

        self._check_button.setEnabled(True)
        results = self._pending_connectivity_checks
        all_online = all(value is MachineStatus.ONLINE for value in results.values())

        lines = []
        for autoclave_name, autoclave_status in results.items():
            if autoclave_status is MachineStatus.ONLINE:
                lines.append(f"{autoclave_name}: OK")
            elif autoclave_status is MachineStatus.OFFLINE:
                lines.append(f"{autoclave_name}: no ok (apagada o desconectada)")
            else:
                lines.append(f"{autoclave_name}: no ok (fallo de conexión)")

        # Respuesta directa a un clic, no un paso de un proceso: no queda
        # nada que consultar luego en el log, se dice y ya está.
        message_type = MessageType.SUCCESS if all_online else MessageType.WARNING
        manager.push(Module.STERIFLOW, message_type, "\n".join(lines))

    def _on_fetch_clicked(self):
        self._backup_runner.run(source="home_page", action=self._controller.backup_service.fetch)

    def _on_run_clicked(self):
        self._backup_runner.run(source="home_page", action=self._controller.backup_service.backup)

    def _on_auto_mode_toggled(self, checked):
        if checked:
            self._controller.start()
        else:
            self._controller.stop()

        # Al log además de decirlo: que la automatización lleve dos semanas
        # apagada y no haya rastro de cuándo se apagó es lo que convierte un
        # despiste en un agujero de trazabilidad.
        estado = "activados" if checked else "desactivados"
        self._agent_logger().log(
            f"Backups automáticos {estado} a mano desde la interfaz",
            talk=MessageType.INFO,
        )
        self._refresh_status_labels()

    def _on_backup_started(self):
        self._fetch_button.setEnabled(False)
        self._run_button.setEnabled(False)

    def _on_backup_finished(self):
        self._fetch_button.setEnabled(True)
        self._run_button.setEnabled(True)
        self._refresh_status_labels()

    def _refresh_status_labels(self):
        self._last_backup_label.setText(f"Último backup: {format_moment(self._controller.last_backup)}")
        self._next_backup_label.setText(f"Próximo backup: {format_moment(self._controller.next_execution)}")
        self._auto_mode_checkbox.setChecked(self._controller.auto_enabled)
