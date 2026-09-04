"""Orquesta el ledger de PDF respaldados y la extracción de su dato de
esterilización. Llamado desde `BackupService` tras replicar hacia el
servidor: primero se deja constancia de qué ha completado el backup, y solo
después se intenta leer el contenido -así una reejecución sin PDF nuevos no
vuelve a comprobar ni a abrir nada ya conocido."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.modules.steriflow.logic.config import SteriflowSettings
from src.shared.logs.logger import Logger
from src.modules.steriflow.logic.sterilization import repo
from src.modules.steriflow.logic.sterilization.hashing import sha256_of
from src.modules.steriflow.logic.sterilization.reader import SteriflowReadError, read_report


def process(
    conn: sqlite3.Connection,
    autoclave: str,
    local_folder: Path,
    backup_folder: Path,
    logger: Logger,
) -> None:
    record_backup_files(conn, autoclave, local_folder, logger)
    extract_pending(conn, autoclave, local_folder, backup_folder, logger)


def record_backup_files(conn: sqlite3.Connection, autoclave: str, local_folder: Path, logger: Logger) -> None:
    if not local_folder.is_dir():
        return
    for pdf in sorted(local_folder.rglob("*.pdf")):
        repo.record_backup_file(conn, autoclave, pdf.name, sha256_of(pdf))
    conn.commit()


def extract_pending(
    conn: sqlite3.Connection,
    autoclave: str,
    local_folder: Path,
    backup_folder: Path,
    logger: Logger,
) -> None:
    pendientes = repo.pending_extraction(conn, autoclave)
    if not pendientes:
        logger.log(f"[{autoclave}] Sin PDF pendientes de extraer")
        return

    logger.log(f"[{autoclave}] {len(pendientes)} PDF pendientes de extraer")
    for fila in pendientes:
        _extract_one(conn, autoclave, fila, local_folder, backup_folder, logger)


def _extract_one(
    conn: sqlite3.Connection,
    autoclave: str,
    fila: sqlite3.Row,
    local_folder: Path,
    backup_folder: Path,
    logger: Logger,
) -> None:
    ruta = _localizar_pdf(fila["filename"], local_folder, backup_folder)
    if ruta is None:
        mensaje = "no se encuentra el fichero ni en local ni en servidor"
        logger.log(f"[{autoclave}]   ERROR extrayendo {fila['filename']}: {mensaje}")
        repo.mark_extracted(conn, fila["id"], error=mensaje)
        conn.commit()
        return

    try:
        ciclo = read_report(ruta)
    except SteriflowReadError as exc:
        logger.log(f"[{autoclave}]   ERROR extrayendo {fila['filename']}: {exc}")
        repo.mark_extracted(conn, fila["id"], error=str(exc))
        conn.commit()
        return
    except Exception as exc:  # PDF corrupto, permisos, fichero en uso...
        logger.log(f"[{autoclave}]   ERROR extrayendo {fila['filename']}: {exc}")
        repo.mark_extracted(conn, fila["id"], error=str(exc))
        conn.commit()
        return

    if not ciclo.batch:
        logger.log(f"[{autoclave}]   Aviso: {fila['filename']} sin lote reconocible en la cabecera")

    _, era_nuevo = repo.save_cycle(conn, ciclo)
    repo.mark_extracted(conn, fila["id"])
    conn.commit()

    estado = "nuevo" if era_nuevo else "actualizado"
    aviso = " (necesita revisión: " + ciclo.review_notes + ")" if ciclo.needs_review else ""
    logger.log(f"[{autoclave}]   Ciclo {estado}{aviso}: {fila['filename']}")


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

    El ciclo no guarda de qué autoclave (config) vino -solo el código que
    imprime la máquina dentro del PDF, que puede no coincidir con el nombre de
    la carpeta (ver `steriflow_backup_file` vs `steriflow_cycle` en
    `schema.py`)-, así que se recorren las carpetas de todas las autoclaves
    configuradas hasta encontrarlo.
    """
    for autoclave in settings.autoclaves:
        ruta = _localizar_pdf(
            source_filename, Path(autoclave.local_folder), Path(autoclave.backup_folder)
        )
        if ruta is not None:
            return ruta
    return None
