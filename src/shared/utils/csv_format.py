"""Detección de delimitador y codificación de un CSV a partir de su
contenido, para lectores que no pueden asumir un único formato fijo -por
ejemplo cuando el mismo tipo de fichero llega exportado por equipos o
versiones de software distintas (ver `modules/ferlo/logic/ingest/reader.py`).

Genérico a propósito: no sabe nada de Ferlo ni de ningún dominio concreto,
así que cualquier otro importador de CSV del proyecto puede reutilizarlo en
vez de repetir su propia detección ad-hoc.
"""

from __future__ import annotations

from pathlib import Path

# BOM -> nombre de codec que ya descarta el propio BOM al decodificar.
_BOM_ENCODINGS: tuple[tuple[bytes, str], ...] = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)


def detect_encoding(path: Path, *, fallback: str = "cp1252") -> str:
    """Adivina la codificación de `path` mirando el BOM y, si no hay, probando
    UTF-8 estricto antes de asumir `fallback`.

    `fallback` es cp1252 porque es lo que ya asumía Ferlo -su equipo manda
    "°C" mal codificado como un único byte-, pero cualquier fichero que sí
    declare su codificación (BOM, o que decodifique limpio como UTF-8) gana
    a esa suposición.
    """
    with path.open("rb") as f:
        head = f.read(4)

    for bom, encoding in _BOM_ENCODINGS:
        if head.startswith(bom):
            return encoding

    try:
        path.read_bytes().decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return fallback


def detect_delimiter(sample_line: str, candidates: tuple[str, ...]) -> str:
    """Elige el primer delimitador de `candidates` que aparece en
    `sample_line` (normalmente una cabecera). Si ninguno aparece, se queda
    con el primero de `candidates` como valor por defecto."""
    for delim in candidates:
        if delim in sample_line:
            return delim
    return candidates[0]
