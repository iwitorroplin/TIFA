from __future__ import annotations

from pathlib import Path


def list_log_files(logs_directory: Path) -> list[Path]:
    """Todos los archivos de log de Steriflow, más reciente primero."""
    try:
        entries = list(logs_directory.glob("*.log"))
    except OSError:
        return []

    return sorted(entries, key=lambda entry: entry.stat().st_mtime, reverse=True)


class LogTailer:
    """Lee solo el contenido nuevo añadido a un archivo desde la última lectura, para
    poder mostrarlo en vivo tipo terminal sin recargar el archivo entero cada vez."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._offset = 0

    def read_new_text(self) -> str:
        try:
            with self.path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(self._offset)
                text = handle.read()
                self._offset = handle.tell()
                return text
        except OSError:
            return ""
