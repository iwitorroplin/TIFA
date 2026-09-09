"""Registro central de módulos: la única fuente de verdad de qué módulos
existen, en qué orden aparecen en la navbar y qué necesitan del resto de la
app (esquema de base de datos, ruta de su log). Navbar y MainWindow generan
sus listas paralelas a partir de aquí en vez de mantener cada una la suya
-desincronizarlas por índice era el bug de siempre-, y LogsView deja de
importar Steriflow directamente: recibe de aquí la lista de módulos con log.

Composition root: es el único sitio del árbol de `modules/` con permiso para
importar más de un módulo a la vez. Ningún módulo debe importar este
fichero -crearía un ciclo con el propio módulo que este fichero ensambla-.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QWidget

from src.shared.assets.resources import APP_ICON
from src.shared.messages.types import Module


@dataclass(frozen=True)
class ModuleSpec:
    id: Module
    label: str
    view: Callable[[], QWidget]
    icon: Path | None = None
    color: str | None = None
    has_logs: bool = False
    ensure_tables: Callable[[sqlite3.Connection], None] | None = None
    log_path: Callable[[], Path] | None = None


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
    from src.modules.logs.ui.view import LogsView
    from src.modules.macona.ui.view import MaconaView
    from src.modules.pasteurization.ui.view import PasteurizationView
    from src.modules.prueba_ui.ui.view import PruebaUIView
    from src.modules.ferlo.logic.schema import ensure_tables as ensure_ferlo_tables
    from src.modules.steriflow.logic.schema import ensure_tables as ensure_steriflow_tables
    from src.modules.steriflow.ui.view import SteriflowView

    core_specs = [
        ModuleSpec(Module.HOME, "Home", HomeView, icon=APP_ICON, color="#3f51b5"),
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
        ModuleSpec(Module.MACONA, "Macona", MaconaView, has_logs=True),
        ModuleSpec(Module.PASTEURIZATION, "Pasteurization", PasteurizationView, has_logs=True),
        ModuleSpec(Module.CONFIG, "Configuración", ConfigView),
    ]

    # LogsView no conoce a ningún módulo por su nombre: recibe (label,
    # log_path) solo de los que se marcan has_logs=True, en ese mismo orden.
    log_sources = [(spec.label, spec.log_path) for spec in core_specs if spec.has_logs]
    logs_spec = ModuleSpec(Module.LOGS, "Logs", lambda: LogsView(log_sources))

    prueba_ui_spec = ModuleSpec(Module.PRUEBA_UI, "Prueba UI", PruebaUIView)

    return [*core_specs, logs_spec, prueba_ui_spec]


# Los imports de cada módulo viven dentro de _build_modules() y no a nivel de
# fichero: aquí es el único sitio con permiso para conocer todos los módulos
# a la vez, y así queda explícito y agrupado en un solo lugar en vez de
# disperso en 8 líneas de import sueltas. ModuleSpec.view guarda la CLASE de
# cada vista (o una fábrica equivalente), no una instancia: MainWindow decide
# cuándo construirlas.
MODULES: list[ModuleSpec] = _build_modules()
