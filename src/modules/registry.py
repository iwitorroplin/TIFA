"""
Registro de módulos: 
    - el orden de estos es el orden en el nav
    - 
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QWidget

from src.shared.messages.types import Module

@dataclass(frozen=True)
class ModuleSpec:
    id: Module
    label: str
    view: Callable[[], QWidget]
    has_logs: bool = False
    ensure_tables: Callable[[sqlite3.Connection], None] | None = None
    log_path: Callable[[], Path] | None = None


# `log_path` es lo que usa housekeeping.py para purgar logs viejos al
# arrancar (ver `_log_directories` ahí): cada módulo con `has_logs=True`
# necesita uno para participar en la limpieza automática. Macona y
# Pasteurization todavía no generan logs, así que no tienen el suyo -si
# empiezan a generarlos, tocará añadirles su propio wrapper igual que estos
# dos-. Repetir este mismo wrapper por cada módulo nuevo no escala: cuando
# haya más de dos, vale la pena unificarlo en una función genérica
# (module_id/nombre -> Path) en vez de una función suelta por módulo.
def _steriflow_log_path() -> Path:
    from src.modules.steriflow.logic.logs import agent_log_path

    return agent_log_path()


def _ferlo_log_path() -> Path:
    from src.modules.ferlo.logic.logs import agent_log_path

    return agent_log_path()


def _build_modules() -> list[ModuleSpec]:
    from src.modules.config.ui.view import ConfigView
    from src.modules.ferlo.ui.view import FerloView
    from src.modules.home.ui.view import HomeView
    from src.modules.macona.ui.view import MaconaView
    from src.modules.pasteurization.ui.view import PasteurizationView
    from src.modules.ferlo.logic.schema import ensure_tables as ensure_ferlo_tables
    from src.modules.steriflow.logic.schema import ensure_tables as ensure_steriflow_tables
    from src.modules.steriflow.ui.view import SteriflowView

    core_specs = [
        ModuleSpec(
            Module.HOME,
            "Home",
            HomeView,
            ),
        ModuleSpec(
            Module.FERLO,
            "Ferlo",
            FerloView,
            has_logs=True,
            ensure_tables=ensure_ferlo_tables,
            log_path=_ferlo_log_path,
            ),
        ModuleSpec(
            Module.STERIFLOW,
            "Steriflow",
            SteriflowView,
            has_logs=True,
            ensure_tables=ensure_steriflow_tables,
            log_path=_steriflow_log_path,
            ),
        ModuleSpec(
            Module.MACONA,
            "Macona", 
            MaconaView, 
            has_logs=True
            ),
        ModuleSpec(
            Module.PASTEURIZATION, 
            "Pasteurization", 
            PasteurizationView, 
            has_logs=True
            ),
        ModuleSpec(
            Module.CONFIG,
            "Configuración",
            ConfigView,
            ),
        ]

    return core_specs

MODULES: list[ModuleSpec] = _build_modules()
