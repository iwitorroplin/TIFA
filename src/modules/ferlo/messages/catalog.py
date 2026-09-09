"""Catálogo de avisos de Ferlo: cada función redacta el texto y decide la
severidad de un evento del módulo, sin decidir por qué canal sale -eso es
cosa de quien la llama, con `src.shared.messages.notice.announce`/`push`
(mismo reparto de canal que `src/modules/steriflow/messages/catalog.py`).

Lo que forma parte de un proceso con historial -una importación, una
asignación de programa- se anuncia con `announce()`: así queda en el log del
módulo igual que lo dice el personaje. Lo que es respuesta directa a un clic
sin nada que registrar -"selecciona un ciclo primero"- se dice con `push()`.

Las líneas de verificación por fichero (`checks.py`) no pasan por aquí: ya
las escribe `logic/ingest/service.py` directamente en el log, sin `talk=`
-son demasiado frecuentes para que valga la pena que las diga un personaje.
"""

from __future__ import annotations

from src.modules.ferlo.logic.analysis.models import CycleStatus, ManualVerdict
from src.modules.ferlo.logic.ingest.service import ImportSummary
from src.shared.messages.notice import Notice
from src.shared.messages.types import MessageType

# --- Importación (ui/import_page.py, tasks/import_runner.py) ---


def import_no_pending(machine: str) -> Notice:
    return Notice(MessageType.INFO, f"{machine}: nada pendiente en la entrada")


def import_finished(machine: str, summary: ImportSummary) -> Notice:
    if not summary.arrivals:
        return import_no_pending(machine)

    ya_vistos = sum(1 for a in summary.arrivals if a.already_seen)
    partes = [f"{len(summary.arrivals)} fichero(s) leído(s)"]
    if ya_vistos:
        partes.append(f"{ya_vistos} ya visto(s)")
    partes.append(f"{summary.total_new_rows} fila(s) nueva(s)")
    partes.append(f"{summary.total_cycles} ciclo(s) analizado(s)")
    texto = f"{machine}: {', '.join(partes)}"

    if summary.total_new_rows == 0:
        return Notice(MessageType.WARNING, texto)
    return Notice(MessageType.SUCCESS, texto)


def import_busy() -> Notice:
    return Notice(MessageType.WARNING, "Ya hay una importación en curso; espera a que termine.")


def import_failed(machine: str, error: object) -> Notice:
    return Notice(MessageType.ERROR, f"ERROR importando {machine}: {error}")


# --- Configuración (ui/config_page.py) ---


def config_saved() -> Notice:
    return Notice(MessageType.SUCCESS, "Configuración de Ferlo guardada")


def config_unchanged() -> Notice:
    return Notice(MessageType.INFO, "No hay cambios que guardar en la configuración de Ferlo")


def config_out_of_range(warnings: list[str]) -> Notice:
    return Notice(MessageType.WARNING, "Guardado con valores fuera de rango:\n" + "\n".join(warnings))


# --- Programas de consigna (ui/config_page.py) ---


def program_saved(code: int) -> Notice:
    return Notice(MessageType.SUCCESS, f"Programa {code:02d} guardado")


def program_code_required() -> Notice:
    return Notice(MessageType.WARNING, "El código de programa es obligatorio.")


# --- Ciclos y detalle (ui/data_page.py, ui/detail_dialog.py) ---

_VERDICT_LABELS = {
    ManualVerdict.NONE: "sin revisar",
    ManualVerdict.CONFORMING: "conforme",
    ManualVerdict.NON_CONFORMING: "no conforme",
}


def verdict_label(verdict: ManualVerdict) -> str:
    return _VERDICT_LABELS[verdict]


_STATUS_LABELS = {
    CycleStatus.OK: "Conforme",
    CycleStatus.REVIEW: "A revisar",
    CycleStatus.NON_CONFORMING: "No conforme",
    CycleStatus.INCOMPLETE: "Incompleto",
    CycleStatus.UNASSIGNED: "Sin programa",
}


def status_label(status: CycleStatus) -> str:
    return _STATUS_LABELS[status]


def verdict_saved(machine: str) -> Notice:
    return Notice(MessageType.SUCCESS, f"Revisión de {machine} guardada")


def program_assigned(machine: str, program_code: int) -> Notice:
    return Notice(MessageType.SUCCESS, f"{machine}: programa {program_code:02d} asignado y ciclo reevaluado")


def program_unassigned(machine: str) -> Notice:
    return Notice(MessageType.SUCCESS, f"{machine}: programa retirado del ciclo")


def assignment_failed() -> Notice:
    """`reassign_program` releé el mensual completo (ver
    `logic/ingest/service.py`) y devuelve `None` en dos casos que no vale la
    pena distinguir en pantalla: el mensual de esa máquina y mes ya no está
    en el archivo, o el ciclo ya no aparece al volver a segmentar -por
    ejemplo, si los umbrales de detección cambiaron entre medias."""
    return Notice(
        MessageType.WARNING,
        "No se pudo reevaluar el ciclo: el mensual del archivo ya no está, o el "
        "ciclo ya no aparece al volver a analizarlo (¿cambiaron los umbrales de "
        "detección desde la última importación?).",
    )
