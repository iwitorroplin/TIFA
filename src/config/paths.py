from __future__ import annotations

from pathlib import Path

# src/config/paths.py -> parents[2] es la raíz del repo.
APP_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = APP_ROOT / "config"


def resolve_path(value: str) -> Path:
    """Si la ruta viene en absoluto (o UNC) se respeta tal cual; si viene en
    relativo, se resuelve contra la carpeta del propio programa (útil para los
    valores por defecto, antes de que alguien la edite desde la pestaña de
    configuración con una ruta real)."""
    path = Path(value)
    return path if path.is_absolute() else APP_ROOT / path
