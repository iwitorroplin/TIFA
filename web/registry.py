"""
Registro central de módulos de la parte web: 
qué módulos existen, en qué orden aparecen en la navbar y qué tabla necesita cada uno. 
Mismo papel que `src/modules/registry.py` para la app de escritorio

Composition root: es el único fichero de `web/` con permiso para importar
más de un `web/modules/<x>` a la vez. Ningún módulo debe importar este
fichero -crearía un ciclo con el propio módulo que este fichero ensambla-.

El esquema de cada módulo se registra aquí mismo, a nivel de fichero, en
cuanto se construye `WEB_MODULES`: el import de este módulo se cachea, así
que el registro ocurre una sola vez por proceso, sin pasar por
`src/__main__.py::_bootstrap()` (eso arrastraría `src.modules.registry` y con
él PySide6 y las 8 vistas de la app de escritorio para leer una lista).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable

from fastapi import APIRouter

from src.shared.db.schema import register_schema


@dataclass(frozen=True)
class WebModuleSpec:
    id: str
    label: str
    router: APIRouter
    ensure_tables: Callable[[sqlite3.Connection], None] | None = None
    # Color del botón en la navbar (ver templates/base.html). 
    # None = gris por defecto
    # -mismo valor por defecto que ModuleSpec.color en
    # src/modules/registry.py, donde solo Home tiene color propio hoy.
    color: str | None = None


def _build_web_modules() -> list[WebModuleSpec]:
    from web.modules.ferlo.routes import router as ferlo_router
    from web.modules.macona.routes import router as macona_router
    from web.modules.pasteurization.routes import router as pasteurization_router
    from web.modules.steriflow.db import ensure_table as ensure_steriflow_web
    from web.modules.steriflow.routes import router as steriflow_router

    return [
        WebModuleSpec("steriflow", "Steriflow", steriflow_router, ensure_steriflow_web),
        WebModuleSpec("ferlo", "Ferlo", ferlo_router),
        WebModuleSpec("macona", "Macona", macona_router),
        WebModuleSpec("pasteurization", "Pasteurization", pasteurization_router),
    ]


WEB_MODULES: list[WebModuleSpec] = _build_web_modules()

for _spec in WEB_MODULES:
    if _spec.ensure_tables is not None:
        register_schema(_spec.ensure_tables)

# web_user no es un módulo de negocio 
from web.modules.user.db import ensure_table as _ensure_user_table

register_schema(_ensure_user_table)
