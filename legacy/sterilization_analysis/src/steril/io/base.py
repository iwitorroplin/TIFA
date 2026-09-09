"""Etapa 1 - Importacion.

Lee el fichero de origen *tal cual*, sin interpretar nada. Toda la
interpretacion (timestamps, validaciones, calibracion) es de la etapa 2.

El registro de lectores es lo que permite anadir otro origen -el sistema
futuro con datos en PDF- como un fichero nuevo, sin tocar el de Ferlo.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class RawTable:
    """Volcado sin interpretar de una tabla de origen."""

    source_path: Path
    sheet_name: str
    headers: list[str]
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    source_sha256: str = ""

    def column_index(self, name: str, *, default: int | None = None) -> int | None:
        """Localiza una columna por cabecera, tolerante a mayusculas y espacios."""
        wanted = _key(name)
        for i, header in enumerate(self.headers):
            if _key(header) == wanted:
                return i
        return default

    def __len__(self) -> int:
        return len(self.rows)


def _key(text: Any) -> str:
    return str(text or "").strip().casefold()


class SourceReader(Protocol):
    """Contrato de un lector de origen."""

    name: str

    def can_read(self, path: Path) -> bool: ...

    def read(self, path: Path, **options: Any) -> RawTable: ...


_READERS: dict[str, SourceReader] = {}


def register_reader(reader: SourceReader) -> SourceReader:
    _READERS[reader.name] = reader
    return reader


def get_reader(name: str) -> SourceReader:
    try:
        return _READERS[name]
    except KeyError:
        disponibles = ", ".join(sorted(_READERS)) or "(ninguno)"
        raise ValueError(
            f"Perfil de origen desconocido: {name!r}. Disponibles: {disponibles}"
        ) from None


def reader_for(path: Path) -> SourceReader:
    for reader in _READERS.values():
        if reader.can_read(path):
            return reader
    raise ValueError(f"Ningun lector registrado admite {path.name}")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
