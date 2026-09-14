"""Orquesta el ledger de PDF respaldados y la extracción de su dato de
esterilización. Son dos acciones separadas, invocables por su cuenta desde
`BackupService`: `record_backup_files` (llamada tras el import, deja
constancia de qué PDF hay en local) y `extract_pending` (la acción manual
"Analizar", que solo lee lo que el ledger diga que aún no se ha leído) -así
una reejecución sin PDF nuevos no vuelve a comprobar ni a abrir nada ya
conocido, y analizar no depende de haber exportado antes.

Aquí es donde el ciclo deja de ser "lo que dice el PDF" y pasa a ser "lo que
dice la planta": el número de autoclave que se guarda es el de la
configuración (`AutoclaveConfig.code`), no el que el informe imprime de sí
mismo. Ver el porqué en `logic/config.py:AutoclaveConfig`.

El logger llega ya con la autoclave puesta como ámbito (`Logger.scoped`), así
que los mensajes de este módulo no repiten el nombre.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.modules.steriflow.logic.config import AutoclaveConfig, SteriflowSettings
from src.shared.logs.logger import Logger
from src.shared.messages.types import MessageType
from src.modules.steriflow.logic.sterilization import repo
from src.modules.steriflow.logic.sterilization.hashing import sha256_of
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle
from src.modules.steriflow.logic.sterilization.reader import SteriflowReadError, read_report


def record_backup_files(conn: sqlite3.Connection, autoclave: str, local_folder: Path, logger: Logger) -> None:
    if not local_folder.is_dir():
        return
    for pdf in sorted(local_folder.rglob("*.pdf")):
        repo.record_backup_file(conn, autoclave, pdf.name, sha256_of(pdf))
    conn.commit()


def extract_pending(
    conn: sqlite3.Connection,
    autoclave: AutoclaveConfig,
    local_folder: Path,
    backup_folder: Path,
    logger: Logger,
) -> None:
    pendientes = repo.pending_extraction(conn, autoclave.name)
    if not pendientes:
        logger.log("Sin PDF pendientes de extraer")
        return

    logger.log(f"{len(pendientes)} PDF pendientes de extraer")
    for fila in pendientes:
        _extract_one(conn, autoclave, fila, local_folder, backup_folder, logger)


def _extract_one(
    conn: sqlite3.Connection,
    autoclave: AutoclaveConfig,
    fila: sqlite3.Row,
    local_folder: Path,
    backup_folder: Path,
    logger: Logger,
) -> None:
    ruta = _localizar_pdf(fila["filename"], local_folder, backup_folder)
    if ruta is None:
        mensaje = "no se encuentra el fichero ni en local ni en servidor"
        logger.log(
            f"  No se pudo extraer {fila['filename']}: {mensaje}", level=MessageType.ERROR
        )
        repo.mark_extracted(conn, fila["id"], error=mensaje)
        conn.commit()
        return

    try:
        ciclo = read_report(ruta)
    except SteriflowReadError as exc:
        logger.log(f"  No se pudo extraer {fila['filename']}: {exc}", level=MessageType.ERROR)
        repo.mark_extracted(conn, fila["id"], error=str(exc))
        conn.commit()
        return
    except Exception as exc:  # PDF corrupto, permisos, fichero en uso...
        logger.log(f"  No se pudo extraer {fila['filename']}: {exc}", level=MessageType.ERROR)
        repo.mark_extracted(conn, fila["id"], error=str(exc))
        conn.commit()
        return

    _aplicar_autoclave(ciclo, autoclave)

    if not ciclo.batch:
        logger.log(
            f"  Aviso: {fila['filename']} sin lote reconocible en la cabecera",
            level=MessageType.WARNING,
        )

    _, era_nuevo = repo.save_cycle(conn, ciclo)
    repo.mark_extracted(conn, fila["id"])
    conn.commit()

    estado = "nuevo" if era_nuevo else "actualizado"
    aviso = " (necesita revisión: " + ciclo.review_notes + ")" if ciclo.needs_review else ""
    logger.log(
        f"  Ciclo {estado}{aviso}: {fila['filename']}",
        level=MessageType.WARNING if ciclo.needs_review else MessageType.INFO,
    )


def _aplicar_autoclave(ciclo: SterilizationCycle, autoclave: AutoclaveConfig) -> None:
    """Sella el ciclo con la autoclave de la que salió el PDF.

    El número real lo pone la configuración y no el informe: la AUTOCLAVE8
    imprime 10 en todos los suyos. Lo que sí se comprueba es que el informe
    diga lo que esa máquina suele decir de sí misma (`code` o `report_code`):
    si no, el PDF está en la carpeta de otra máquina y el ciclo se guardaría
    bajo una autoclave que no es la que lo hizo -así al menos queda marcado
    para que alguien lo mire, en vez de colarse en silencio-.
    """
    impreso = ciclo.reported_code
    ciclo.autoclave = autoclave.name
    ciclo.autoclave_code = autoclave.code

    if impreso is not None and impreso not in (autoclave.code, autoclave.report_code):
        ciclo.needs_review = True
        nota = (
            f"El informe dice autoclave {impreso} y está en la carpeta de "
            f"{autoclave.name} (que imprime {autoclave.report_code}): "
            f"se guarda como autoclave {autoclave.code}"
        )
        ciclo.review_notes = f"{ciclo.review_notes}; {nota}" if ciclo.review_notes else nota


def _localizar_pdf(filename: str, local_folder: Path, backup_folder: Path) -> Path | None:
    """El PDF vive tanto en local como en servidor -robocopy replica uno a
    uno-, pero local es disco del propio PC y el servidor puede ser una ruta
    de red: se prefiere local por velocidad, y se cae al servidor solo si ya
    no está en el staging local."""
    local_path = local_folder / filename
    if local_path.is_file():
        return local_path
    backup_path = backup_folder / filename
    if backup_path.is_file():
        return backup_path
    return None


def find_pdf(settings: SteriflowSettings, source_filename: str) -> Path | None:
    """Busca el PDF de un ciclo ya guardado, para abrirlo desde la interfaz.

    Se recorren las carpetas de todas las autoclaves configuradas en vez de ir
    directo a la del ciclo: el fichero puede haberse movido de máquina o venir
    de un ciclo guardado antes de que se guardara el nombre de la autoclave, y
    buscar en todas cuesta lo mismo que acertar a la primera.
    """
    for autoclave in settings.autoclaves:
        ruta = _localizar_pdf(
            source_filename, Path(autoclave.local_folder), Path(autoclave.backup_folder)
        )
        if ruta is not None:
            return ruta
    return None
