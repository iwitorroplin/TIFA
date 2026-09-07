"""Único ancla de rutas del proyecto. Todo lo demás (config, assets, db) se
calcula a partir de PROJECT_ROOT en vez de repetir su propio `parents[N]`,
que se desincroniza en silencio en cuanto un fichero cambia de profundidad.
"""

from __future__ import annotations

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
# Logs que no son de ningún módulo (ver src/app/housekeeping.py); los de
# cada módulo cuelgan de su propia configuración.
LOGS_DIR = DATA_DIR / "logs"
# Aquí y no en housekeeping.py: la pestaña de Configuración también escribe
# en él, y housekeeping importa el registro de módulos -importarlo desde
# un módulo cerraría el ciclo-.
APP_LOG_PATH = LOGS_DIR / "tifa.log"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
