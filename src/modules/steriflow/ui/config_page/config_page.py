from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QVBoxLayout, QWidget

from src.modules.steriflow.logic.controller import SteriflowController
from src.modules.steriflow.logic.logs import agent_logger
from src.modules.steriflow.logic.settings_editor import SaveStatus
from src.modules.steriflow.messages import catalog
from src.modules.steriflow.ui.config_page.config_presenter import SteriflowConfigPresenter
from src.shared.messages.notice import announce, push
from src.shared.messages.types import Module
from src.shared.ui.components.app_button import AppButton, AppSaveButton

from src.modules.steriflow.ui.config_page.autoclaves_group import AutoclavesGroup
from src.modules.steriflow.ui.config_page.columns_dialog import ColumnsDialog
from src.modules.steriflow.ui.config_page.paths_group import PathsGroup
from src.modules.steriflow.ui.config_page.schedules_dialog import SchedulesDialog


class SteriflowConfigPage(QWidget):
    def __init__(self, controller: SteriflowController):
        super().__init__()

        self._presenter = SteriflowConfigPresenter(controller)

        self._dirty = False

        self._paths_group = PathsGroup(self._presenter, self._mark_dirty)
        self._autoclaves_group = AutoclavesGroup(self._presenter, self._mark_dirty)

        layout = QVBoxLayout(self)
        layout.addWidget(self._paths_group)
        layout.addWidget(self._autoclaves_group)
        layout.addWidget(self._build_advanced_group())
        layout.addStretch()
        layout.addLayout(self._build_save_bar())

        self._repaint()

    def _build_advanced_group(self):
        # Horarios y columnas visibles son datos que se tocan poco: viven en
        # modales aparte para no ocupar sitio permanente en la página (ver
        # discusión del refactor de config_page).
        group = QGroupBox("Configuración avanzada")

        schedules_button = AppButton("Horarios...")
        schedules_button.clicked.connect(self._open_schedules_dialog)

        columns_button = AppButton("Columnas...")
        columns_button.clicked.connect(self._open_columns_dialog)

        layout = QHBoxLayout(group)
        layout.addWidget(schedules_button)
        layout.addWidget(columns_button)
        layout.addStretch()

        return group

    def _open_schedules_dialog(self):
        dialog = SchedulesDialog(self._presenter, self._mark_dirty, self)
        dialog.exec()

    def _open_columns_dialog(self):
        dialog = ColumnsDialog(self._presenter, self._mark_dirty, self)
        dialog.exec()

    def _repaint(self):
        """Repinta todo desde el presenter, nunca al revés: así la tabla
        nunca puede desincronizarse de lo que hay realmente en el borrador
        (ver el riesgo de índices desalineados en el histórico del refactor).
        El estado de red de cada autoclave ya no vive aquí: se ve en el
        groupbox de estado de la home page."""
        self._paths_group.repaint()
        self._autoclaves_group.repaint()

    # --- guardado explícito: cada acción puntual (elegir una carpeta, aceptar
    # el diálogo de autoclave/horario, quitar una fila) solo marca el borrador
    # como sucio; el guardado en disco espera al botón "Guardar cambios" ---

    def _build_save_bar(self):
        self._save_button = AppSaveButton("Guardar cambios")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._on_save_clicked)

        discard_button = AppButton("Descartar cambios", color="#8a8a8a")
        discard_button.clicked.connect(self._on_discard_clicked)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(discard_button)
        row.addWidget(self._save_button)
        return row

    def _mark_dirty(self):
        self._dirty = True
        self._save_button.setEnabled(True)
        self._repaint()

    def _on_save_clicked(self):
        outcome = self._presenter.save()
        self._repaint()

        if outcome.status is SaveStatus.INVALID:
            push(Module.STERIFLOW, catalog.settings_issue(outcome.issue))
            return

        if outcome.status is SaveStatus.UNCHANGED:
            push(Module.STERIFLOW, catalog.settings_unchanged())
        else:
            # El log es lo que explica meses después por qué el backup dejó de
            # copiar: alguien cambió una ruta tal día.
            announce(agent_logger(), catalog.settings_saved())

        self._dirty = False
        self._save_button.setEnabled(False)

    def _on_discard_clicked(self):
        self._presenter.load()
        self._repaint()
        self._dirty = False
        self._save_button.setEnabled(False)
