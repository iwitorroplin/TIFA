"""Funciones de Steriflow pensadas para correr en un hilo de fondo.

Misma regla que en `services.jobs`: cada una abre y cierra su propia conexion,
porque un `sqlite3.Connection` no se puede usar desde un hilo distinto al que
lo creo. Aqui pesa mas que en Ferlo -abrir un PDF cuesta ~320 ms y una carpeta
de produccion tiene miles-, asi que importar sin salir del hilo de la interfaz
la dejaria congelada minutos.
"""

from __future__ import annotations

from ..core.config import Settings
from ..storage.schema import connect
from .service import OnProgress, ShouldCancel, SteriflowIngestResult, ingest_all


def import_reports_job(
    settings: Settings,
    force: bool = False,
    on_progress: OnProgress | None = None,
    should_cancel: ShouldCancel | None = None,
) -> list[SteriflowIngestResult]:
    conn = connect(settings.paths["database_path"])
    try:
        return ingest_all(
            conn, 
            settings,
            force=force,
            on_progress=on_progress,
            should_cancel=should_cancel,
        )
    finally:
        conn.close()
