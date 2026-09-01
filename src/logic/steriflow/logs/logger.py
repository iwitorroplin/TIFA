from __future__ import annotations

from datetime import datetime
from pathlib import Path


class Logger:
    def __init__(self, log_file_path: Path) -> None:
        self.log_file_path = log_file_path

        try:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] No se pudo preparar la carpeta de logs '{self.log_file_path}': {ex}")

    def log(self, message: str) -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
        print(line)

        try:
            with self.log_file_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as ex:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] No se pudo escribir en el log '{self.log_file_path}': {ex}")
