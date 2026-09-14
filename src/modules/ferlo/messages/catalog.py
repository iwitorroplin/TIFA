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
from src.modules.ferlo.logic.ingest.pending import PendingReport
from src.modules.ferlo.logic.ingest.service import BatchSummary, ImportSummary
from src.shared.messages.notice import Notice
from src.shared.messages.types import MessageType

# --- Importación (ui/home_page/, tasks/import_runner.py) ---


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


# --- Acciones sobre las cinco máquinas (ui/home_page/) ---


def check_finished(report: PendingReport) -> Notice:
    """Lo que encontró el check en las entradas. Los ficheros ya llegados se
    dicen aparte y no cuentan como novedad: son los que la importación va a
    descartar por sha256 (ver `logic/ingest/pending.py`), y presentarlos como
    pendientes prometería datos nuevos que no existen."""
    if not report.machines:
        return Notice(MessageType.INFO, "No hay máquinas configuradas")

    if report.total_new == 0 and report.total_already_arrived == 0:
        return Notice(MessageType.INFO, "Nada pendiente en las entradas de las cinco máquinas")

    if report.total_new == 0:
        return Notice(
            MessageType.WARNING,
            f"Sin datos nuevos: los {report.total_already_arrived} fichero(s) de la "
            "entrada ya se habían importado antes",
        )

    detalle = ", ".join(
        f"{m.machine} ({len(m.new_files)})" for m in report.machines if m.has_new
    )
    texto = f"{report.total_new} fichero(s) nuevo(s) por importar: {detalle}"
    if report.total_already_arrived:
        texto += f" · {report.total_already_arrived} ya visto(s)"
    return Notice(MessageType.SUCCESS, texto)


def _failures_suffix(batch: BatchSummary) -> str:
    if not batch.failures:
        return ""
    maquinas = ", ".join(machine for machine, _ in batch.failures)
    return f" · falló {maquinas}"


def import_all_finished(batch: BatchSummary) -> Notice:
    """Resultado de importar las cinco máquinas de una pasada.

    Las filas descartadas por solape se dicen siempre que las haya: sin eso,
    reimportar un CSV que ya venía cubierto se lee como "0 filas nuevas" y no
    hay forma de distinguirlo de un fichero vacío o mal leído.
    """
    if batch.failures and not batch.summaries:
        return Notice(MessageType.ERROR, f"No se pudo importar ninguna máquina{_failures_suffix(batch)}")

    if batch.total_arrivals == 0:
        return Notice(
            MessageType.WARNING if batch.failures else MessageType.INFO,
            f"Nada pendiente en las entradas{_failures_suffix(batch)}",
        )

    ya_vistos = sum(
        1 for s in batch.summaries for a in s.arrivals if a.already_seen
    )
    partes = [
        f"{batch.total_arrivals} fichero(s) de {len(batch.machines_with_arrivals)} máquina(s)",
    ]
    if ya_vistos:
        partes.append(f"{ya_vistos} ya importado(s) antes (mismos bytes)")
    partes.append(f"{batch.total_new_rows} fila(s) nueva(s)")
    partes.append(f"{batch.total_cycles} ciclo(s) analizado(s)")
    if batch.total_duplicate_rows:
        partes.append(f"{batch.total_duplicate_rows} fila(s) duplicada(s) descartada(s)")
    texto = ", ".join(partes) + _failures_suffix(batch)

    if batch.failures or batch.total_new_rows == 0:
        return Notice(MessageType.WARNING, texto)
    return Notice(MessageType.SUCCESS, texto)


def analysis_finished(batch: BatchSummary) -> Notice:
    if batch.failures and not batch.summaries:
        return Notice(MessageType.ERROR, f"No se pudo reanalizar ninguna máquina{_failures_suffix(batch)}")

    meses = sum(len(s.cycles_by_month) for s in batch.summaries)
    texto = f"{batch.total_cycles} ciclo(s) reanalizado(s) en {meses} mes(es)" + _failures_suffix(batch)
    return Notice(MessageType.WARNING if batch.failures else MessageType.SUCCESS, texto)


def no_archived_months() -> Notice:
    return Notice(MessageType.INFO, "No hay mensuales en el archivo todavía: importa antes.")


def action_busy() -> Notice:
    return Notice(MessageType.WARNING, "Ya hay una acción en curso; espera a que termine.")


def action_failed(error: object) -> Notice:
    return Notice(MessageType.ERROR, f"ERROR en la acción de Ferlo: {error}")


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


def manual_setpoint_assigned(
    machine: str, target_temperature_c: float, target_time_min: float
) -> Notice:
    """Consigna tecleada a mano en vez de elegida de la lista. Dice los
    valores y no "programa 00": el 0 es una fila centinela para la clave
    ajena (ver `logic/schema.py`), no un programa que nadie reconozca."""
    return Notice(
        MessageType.SUCCESS,
        f"{machine}: consigna manual {target_temperature_c:.0f} °C / "
        f"{target_time_min:.0f} min asignada y ciclo reevaluado",
    )


def manual_setpoints_assigned(
    reassigned: int, selected: int, target_temperature_c: float, target_time_min: float
) -> Notice:
    """Igual que `programs_assigned`, pero para la consigna manual en bloque."""
    tipo = MessageType.SUCCESS if reassigned == selected else MessageType.WARNING
    return Notice(
        tipo,
        f"Consigna manual {target_temperature_c:.0f} °C / {target_time_min:.0f} min: "
        f"{reassigned} de {selected} ciclos reevaluados",
    )


def program_unassigned(machine: str) -> Notice:
    return Notice(MessageType.SUCCESS, f"{machine}: programa retirado del ciclo")


def programs_assigned(reassigned: int, selected: int, program_code: int | None) -> Notice:
    """Resultado de asignar en bloque desde la pestaña de Ciclos.

    Dice siempre los dos números, no solo el de los que salieron bien: si de
    30 ciclos seleccionados solo se reasignan 28, un "28 ciclos actualizados"
    a secas se leería como un éxito completo.
    """
    que = "programa retirado de" if program_code is None else f"programa {program_code:02d} asignado a"

    if reassigned == 0:
        return Notice(
            MessageType.WARNING,
            f"Ningún ciclo de los {selected} seleccionados se pudo reevaluar: "
            "¿está el mensual del archivo en su sitio?",
        )
    if reassigned < selected:
        return Notice(
            MessageType.WARNING,
            f"{que} {reassigned} de {selected} ciclo(s): el resto ya no aparece al "
            "volver a analizar su mensual",
        )
    return Notice(MessageType.SUCCESS, f"{que} {reassigned} ciclo(s), ya reevaluados")


def no_cycles_selected_to_assign() -> Notice:
    return Notice(MessageType.WARNING, "Selecciona antes los ciclos a los que asignar el programa")


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
