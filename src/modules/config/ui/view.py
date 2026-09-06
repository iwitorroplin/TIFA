from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.shared.config import app_config
from src.shared.logs.logger import Logger
from src.shared.messages.types import MessageType, Module
from src.shared.paths import APP_LOG_PATH

_MAX_RETENTION_MONTHS = 120

# Igual que en el filtro de la tabla de ciclos: se espera a que el usuario
# pare. Sin esto, subir de 6 a 24 meses con la flecha del spinbox guardaría
# dieciocho veces y soltaría dieciocho avisos.
_SAVE_DELAY_MS = 700


class ConfigView(QWidget):
    """Configuración de la aplicación entera, no de un módulo concreto: lo que
    cada módulo configura por su cuenta vive en su propia pestaña (rutas, IPs y
    horarios de Steriflow, por ejemplo)."""

    def __init__(self):
        super().__init__()

        self._retention_months = app_config.load_settings().logs_retention_months

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(_SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._save_retention)

        layout = QVBoxLayout(self)
        layout.addWidget(QCheckBox("Iniciar TIFA al iniciar sesión de Windows"))
        layout.addWidget(self._build_logs_group())
        layout.addStretch()

    def _build_logs_group(self):
        group = QGroupBox("Historial de logs")

        self._retention_spin = QSpinBox()
        self._retention_spin.setRange(0, _MAX_RETENTION_MONTHS)
        self._retention_spin.setSuffix(" meses")
        # El texto especial sustituye al valor mínimo (0): "0 meses" se leería
        # como "borrar todo", que es justo lo contrario de lo que hace.
        self._retention_spin.setSpecialValueText("No borrar nunca")
        self._retention_spin.setValue(self._retention_months)
        self._retention_spin.valueChanged.connect(lambda _value: self._save_timer.start())

        explanation = QLabel(
            "Cada ejecución de backup deja su propio fichero de log, así que la carpeta "
            "crece sola. Los más viejos se borran al arrancar la aplicación; el cambio "
            "se aplica en el próximo arranque."
        )
        explanation.setWordWrap(True)

        group_layout = QFormLayout(group)
        group_layout.addRow("Borrar los logs con más de:", self._retention_spin)
        group_layout.addRow(explanation)

        return group

    def _save_retention(self):
        months = self._retention_spin.value()
        if months == self._retention_months:
            return

        self._retention_months = months
        app_config.save_logs_retention_months(months)

        detalle = (
            f"se borrarán al arrancar los de más de {months} mes(es)"
            if months
            else "no se borrará ninguno automáticamente"
        )
        Logger(APP_LOG_PATH, Module.CONFIG).log(
            f"Retención de logs cambiada: {detalle}", talk=MessageType.SUCCESS
        )
