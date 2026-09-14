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

from src.modules.steriflow.logic.controller import SteriflowController
from src.modules.steriflow.logic.logs import STERIFLOW_LOGS_ROOT, agent_logger
from src.modules.steriflow.logic.network import MachineStatus
from src.shared.assets.paths import STATUS_GREEN, STATUS_GREY, STATUS_RED, STATUS_YELLOW
from src.shared.ui.components.app_button import (
    AppButton,
    AppFolderButton,
    AppStartButton,
    AppStatusButton,
)

from src.shared.utils.formatting import format_moment
from src.modules.steriflow.messages import catalog
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.modules.steriflow.tasks.backup_runner import BackupRunner
from src.modules.steriflow.tasks.status_checker import AutoclaveStatusChecker
from src.shared.ui.components.loading_overlay import LoadingOverlay


# Mismo mapeo que la columna "Estado" de la pestaña Configuración (ver
# ui/config_page/autoclaves_group.py): iconos de materia, decoración pura, la
# etiqueta la sigue dando catalog.machine_status_label.
_STATUS_ICONS = {
    MachineStatus.ONLINE: STATUS_GREEN,
    MachineStatus.OFFLINE: STATUS_RED,
    MachineStatus.CONNECTION_ERROR: STATUS_YELLOW,
}



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
        layout.addWidget(self._build_automation_status_group())
        layout.addWidget(self._build_status_machine_group())
        layout.addWidget(self._build_backup_actions_group())
        layout.addWidget(self._build_open_folders_group())
        layout.addStretch()

        # Cubre toda la página mientras corre una acción (check/import/export):
        # bloquea los clics del resto sin tener que deshabilitar cada botón a
        # mano, y evita el parpadeo si la acción termina casi al instante.
        self._loading_overlay = LoadingOverlay(self)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_status_labels()
        self._status_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._status_timer.stop()


    def _build_automation_status_group(self):
        group = QGroupBox("Estado de la automatización")

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

    def _build_status_machine_group(self):
        """Un botón-chip por autoclave activa con su icono de estado (ver
        _STATUS_ICONS): da de un vistazo lo que antes solo se veía en la
        columna "Estado" de la pestaña Configuración, y cada chip vuelve a
        comprobar esa máquina en concreto al pulsarlo, sin relanzar el check
        de todas (ver _on_status_button_clicked)."""
        group = QGroupBox("Estado de las autoclaves")

        self._status_buttons: dict[str, AppStatusButton] = {}
        group_layout = QHBoxLayout(group)

        autoclaves = [a for a in self._controller.settings.autoclaves if a.active]
        for autoclave in autoclaves:
            button = AppStatusButton(autoclave.name, STATUS_GREY)
            button.setToolTip("Sin comprobar todavía. Pulsa para comprobar esta autoclave.")
            button.clicked.connect(lambda _checked=False, name=autoclave.name: self._on_status_button_clicked(name))
            self._status_buttons[autoclave.name] = button
            group_layout.addWidget(button)

        group_layout.addStretch()
        return group

    def _build_backup_actions_group(self):
        group = QGroupBox("Acciones de Backup")

        self._check_button = AppStartButton("check")
        self._check_button.setToolTip ("Comprueba la conexion de las maquinas")
        self._check_button.clicked.connect(self._on_check_clicked)

        self._fetch_button = AppStartButton("Import")
        self._fetch_button.setToolTip("Importa los datos (.pdf) de las maquinas a local")
        self._fetch_button.clicked.connect(self._on_fetch_clicked)

        self._analyze_button = AppStartButton("Analizar")
        self._analyze_button.setToolTip("Extrae el dato de esterilización de los PDF pendientes en local")
        self._analyze_button.clicked.connect(self._on_analyze_clicked)

        self._backup_button = AppStartButton("Export")
        self._backup_button.setToolTip("Exporta los datos (.pdf) de las maquinas al servidor")
        self._backup_button.clicked.connect(self._on_backup_clicked)

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(self._check_button)
        group_layout.addWidget(self._fetch_button)
        group_layout.addWidget(self._analyze_button)
        group_layout.addWidget(self._backup_button)
        group_layout.addStretch()

        return group

    def _build_open_folders_group(self):
        group = QGroupBox("Abrir carpetas")

        logger = agent_logger()
        paths = self._controller.settings.paths

        open_logs_button = AppFolderButton("Abrir logs", STERIFLOW_LOGS_ROOT, logger, create=True)
        open_local_button = AppFolderButton("Abrir Local", paths.local_root, logger, create=True)
        open_server_button = AppFolderButton("Abrir Servidor", paths.server_root, logger, create=False)

        group_layout = QHBoxLayout(group)
        group_layout.addWidget(open_logs_button)
        group_layout.addWidget(open_local_button)
        group_layout.addWidget(open_server_button)
        group_layout.addStretch()

        return group


    def _on_check_clicked(self):
        autoclaves = [a for a in self._controller.settings.autoclaves if a.active]
        if not autoclaves:
            push(Module.STERIFLOW, catalog.no_active_autoclaves())
            return

        self._loading_overlay.start("Comprobando conexión...")
        self._pending_connectivity_checks = {autoclave.name: None for autoclave in autoclaves}
        self._connectivity_checker.check([(a.name, a.ip) for a in autoclaves])

    def _on_status_button_clicked(self, name):
        # Chip individual: relanza el check solo de esta autoclave, sin
        # esperar a que las demás terminen ni tapar la página con el overlay
        # -es una comprobación puntual, no una acción de grupo.
        button = self._status_buttons.get(name)
        if button is None:
            return
        autoclave = next((a for a in self._controller.settings.autoclaves if a.name == name), None)
        if autoclave is None:
            return
        self._connectivity_checker.check([(autoclave.name, autoclave.ip)])

    def _on_connectivity_checked(self, name, status: MachineStatus):
        button = self._status_buttons.get(name)
        if button is not None:
            button.set_icon(_STATUS_ICONS[status])
            button.setToolTip(catalog.machine_status_label(status))

        if name not in self._pending_connectivity_checks:
            return
        self._pending_connectivity_checks[name] = status
        if any(value is None for value in self._pending_connectivity_checks.values()):
            return

        self._loading_overlay.finish()
        # Respuesta directa a un clic, no un paso de un proceso: no queda
        # nada que consultar luego en el log, se dice y ya está.
        push(Module.STERIFLOW, catalog.connectivity_report(list(self._pending_connectivity_checks.items())))

    def _on_fetch_clicked(self):
        self._backup_runner.run(source="home_page", action=self._controller.backup_service.fetch)

    def _on_analyze_clicked(self):
        if not self._controller.backup_service.has_pending_analysis():
            push(Module.STERIFLOW, catalog.no_pending_analysis())
            return
        self._backup_runner.run(source="home_page", action=self._controller.backup_service.analyze)

    def _on_backup_clicked(self):
        self._backup_runner.run(source="home_page", action=self._controller.backup_service.backup)

    def _on_auto_mode_toggled(self, checked):
        self._controller.set_auto_enabled(checked)

        # Al log además de decirlo: que la automatización lleve dos semanas
        # apagada y no haya rastro de cuándo se apagó es lo que convierte un
        # despiste en un agujero de trazabilidad.
        announce(agent_logger(), catalog.auto_mode_changed(checked))
        self._refresh_status_labels()

    def _on_backup_started(self):
        self._loading_overlay.start()

    def _on_backup_finished(self):
        self._loading_overlay.finish()
        self._refresh_status_labels()

    def _refresh_status_labels(self):
        self._last_backup_label.setText(f"Último backup: {format_moment(self._controller.last_backup)}")
        self._next_backup_label.setText(f"Próximo backup: {format_moment(self._controller.next_execution)}")
        self._auto_mode_checkbox.setChecked(self._controller.auto_enabled)
