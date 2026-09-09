"""
Catálogo de avisos de Steriflow: cada función redacta el texto y decide
la severidad de un evento del módulo, sin decidir por qué canal sale -eso es
cosa de quien la llama, con `src.shared.messages.notice.announce`/`push`.

Reparto de canal: lo que merece quedar en el log lo anuncia la lógica con
`announce()`, para que salga igual venga de un botón o del scheduler
nocturno; lo que es respuesta directa a un clic, sin nada que registrar,
lo dice la página con `push()`. Todos los avisos del módulo van por los
personajes (ver `MessageBar`); no hay un segundo canal de diálogo síncrono
-lo hubo (`src.shared.ui.notices.show`) hasta que dejó de tener ningún
llamador-. Quedan fuera de este catálogo, a propósito: las líneas de log
sin `talk=`, y las etiquetas estáticas de widgets (títulos de QGroupBox,
botones, cabeceras de tabla).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Sequence

from src.modules.steriflow.logic.network import MachineStatus
from src.modules.steriflow.logic.settings_editor import AutoclaveIssue, SettingsIssue
from src.shared.messages.notice import Notice
from src.shared.messages.types import MessageType


# --- Fin de una ejecución de backup (logic/backup/service.py) ---

def full_backup_finished(incidents: int) -> Notice:
    return _finished("Backup Steriflow finalizado", incidents)


def fetch_finished(incidents: int) -> Notice:
    return _finished("Importación de las máquinas realizada", incidents)


def fetch_no_machines_reachable() -> Notice:
    """Sin incidencias pero sin ninguna autoclave disponible: no queda nada
    que consultar en el log, así que no puede salir como SUCCESS -no se ha
    traído nada- (ver `BackupService.fetch`)."""
    return Notice(MessageType.WARNING, "Importación de las máquinas no realizada: ninguna autoclave respondió")


def server_backup_finished(incidents: int) -> Notice:
    return _finished("Exportación al servidor realizada", incidents)


def _finished(done_message: str, incidents: int) -> Notice:
    if incidents:
        return Notice(
            MessageType.WARNING,
            f"{done_message}, con {incidents} incidencia(s): ver el detalle más arriba en este log",
        )
    return Notice(MessageType.SUCCESS, done_message)


# --- Backup automático (logic/backup/scheduler.py) ---

def scheduled_backup_failed(error: object) -> Notice:
    return Notice(MessageType.ERROR, f"Error durante la ejecución del backup programado: {error}")


# --- Backup manual (tasks/backup_runner.py) ---

def manual_backup_busy(source: str) -> Notice:
    return Notice(MessageType.WARNING, f"Backup manual desde {source} ignorado: ya hay una acción en curso")


def manual_backup_failed(error: object) -> Notice:
    return Notice(MessageType.ERROR, f"ERROR en backup manual: {error}")


# --- Configuración (ui/config_page.py) ---

def settings_saved() -> Notice:
    return Notice(MessageType.SUCCESS, "Configuración de Steriflow guardada")


def settings_unchanged() -> Notice:
    return Notice(MessageType.INFO, "No hay cambios que guardar en la configuración de Steriflow")


_SETTINGS_ISSUE_TEXTS = {
    SettingsIssue.LOCAL_ROOT_REQUIRED: "La carpeta raíz local es obligatoria.",
    SettingsIssue.SERVER_ROOT_REQUIRED: "La carpeta raíz de servidor es obligatoria.",
    SettingsIssue.AT_LEAST_ONE_SCHEDULE: "Debe quedar al menos un horario configurado.",
}


def settings_issue(issue: SettingsIssue) -> Notice:
    return Notice(MessageType.WARNING, _SETTINGS_ISSUE_TEXTS[issue])


_AUTOCLAVE_ISSUE_TEXTS = {
    AutoclaveIssue.SOURCE_FOLDER_REQUIRED: "La carpeta origen es obligatoria.",
    AutoclaveIssue.LOCAL_FOLDER_REQUIRED: "La carpeta local es obligatoria.",
    AutoclaveIssue.BACKUP_FOLDER_REQUIRED: "La carpeta de backup es obligatoria.",
}


def autoclave_issue(issue: AutoclaveIssue) -> Notice:
    return Notice(MessageType.WARNING, _AUTOCLAVE_ISSUE_TEXTS[issue])


# --- Conectividad y estado de red (ui/home_page.py, ui/config_page.py) ---

def no_active_autoclaves() -> Notice:
    return Notice(MessageType.WARNING, "No hay autoclaves activas configuradas.")


_STATUS_LABELS = {
    MachineStatus.ONLINE: "En línea",
    MachineStatus.OFFLINE: "Apagada",
    MachineStatus.CONNECTION_ERROR: "Fallo de conexión",
}


def machine_status_label(status: MachineStatus) -> str:
    """Etiqueta de estado, no un aviso: la comparten la columna "Estado" de
    la pestaña Configuración y las líneas de `connectivity_report`."""
    return _STATUS_LABELS[status]


def connectivity_report(results: Sequence[tuple[str, MachineStatus]]) -> Notice:
    lines = []
    all_online = True
    for name, status in results:
        if status is MachineStatus.ONLINE:
            lines.append(f"{name}: OK")
        else:
            all_online = False
            lines.append(f"{name}: No OK: {machine_status_label(status)}")

    message_type = MessageType.SUCCESS if all_online else MessageType.WARNING
    return Notice(message_type, "\n".join(lines))


# --- Modo automático (ui/home_page.py) ---

def auto_mode_changed(enabled: bool) -> Notice:
    state = "activados" if enabled else "desactivados"
    return Notice(MessageType.INFO, f"Backups automáticos {state} a mano desde la interfaz")


# --- Ciclos de esterilización (ui/data_page.py) ---

class OpenFailure(Enum):
    NOT_FOUND = "not_found"
    CANNOT_OPEN = "cannot_open"


_OPEN_FAILURE_TEXTS = {
    OpenFailure.NOT_FOUND: "no se encuentra el fichero",
    OpenFailure.CANNOT_OPEN: "el sistema no pudo abrirlo",
}


def no_cycles_selected_to_open() -> Notice:
    return Notice(MessageType.INFO, "Selecciona al menos un ciclo.")


def no_cycles_selected_to_print() -> Notice:
    return Notice(MessageType.INFO, "Selecciona al menos un ciclo para imprimir.")


def no_cycles_selected_to_export() -> Notice:
    return Notice(MessageType.INFO, "Selecciona al menos un ciclo para guardar.")


def pdfs_not_opened(failures: Sequence[tuple[str, OpenFailure]]) -> Notice:
    lines = [f"{filename}: {_OPEN_FAILURE_TEXTS[reason]}" for filename, reason in failures]
    return Notice(MessageType.WARNING, "No se pudieron abrir:\n" + "\n".join(lines))


def cycles_pdf_saved(count: int, destination: Path) -> Notice:
    return Notice(MessageType.SUCCESS, f"PDF de {count} ciclo(s) guardado en {destination}")


def cycles_pdf_save_failed(destination: Path, error: object) -> Notice:
    return Notice(MessageType.ERROR, f"No se pudo guardar el PDF '{destination}': {error}")
