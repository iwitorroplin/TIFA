"""Qué informes hay en una carpeta y todavía no en la otra.

Lo usan las dos mitades del backup (traer de la autoclave, replicar al servidor)
y la comprobación de disponibilidad, que necesita saber si hay algo nuevo sin
tocar nada.
"""

from __future__ import annotations

from pathlib import Path

_PDF_PATTERN = "*.pdf"


def new_reports(source: Path, target: Path) -> list[Path]:
    """PDF que ya están en `source` pero todavía no en `target`, por ruta relativa.

    El destino nunca se purga (ver `run_robocopy`), así que su contenido es el
    historial de lo ya copiado: lo que está en el origen y no en el destino es
    justo lo que falta por copiar, sea de esta ejecución o de una anterior que
    no llegó a replicar.

    Un origen inexistente da lista vacía, pero un origen que existe y no se deja
    leer levanta OSError: quien pregunte por una carpeta de red decide si eso es
    un error (el backup) o un "no se pudo mirar" (la comprobación de disponibilidad).
    """
    if not source.is_dir():
        return []

    ya_copiados = (
        {p.relative_to(target) for p in target.rglob(_PDF_PATTERN)}
        if target.is_dir() else set()
    )
    return sorted(
        (p for p in source.rglob(_PDF_PATTERN) if p.relative_to(source) not in ya_copiados),
        key=lambda p: p.relative_to(source),
    )
