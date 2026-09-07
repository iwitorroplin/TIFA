"""Objeto `Jinja2Templates` compartido por toda la parte web.

Busca en el `web/templates/` común (layout base, home) y en la carpeta
`templates/` de cada `web/modules/<x>/` que la tenga -en ese orden, y
descubierta con un glob en vez de con una lista a mano: así un módulo nuevo
con su propia plantilla no requiere tocar este fichero, solo crear su
carpeta. `{% extends "base.html" %}` encuentra el layout común sea cual sea
el módulo que lo pida.

Jinja2 busca en esa lista de directorios EN ORDEN y se queda con la primera
plantilla que encuentre por nombre: si dos módulos (o un módulo y lo
compartido) usaran el mismo nombre de fichero, uno taparía al otro en
silencio. Por eso cada módulo prefija sus propias plantillas con su nombre
-`steriflow_inicio.html`, no `inicio.html`- en vez de con subcarpetas: no
puede chocar ni con `web/templates/` ni con el `<x>_...html` de otro módulo.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

_WEB_ROOT = Path(__file__).resolve().parent
_TEMPLATES_DIR = _WEB_ROOT / "templates"
_MODULES_DIR = _WEB_ROOT / "modules"


def _module_template_dirs() -> list[Path]:
    return sorted(p for p in _MODULES_DIR.glob("*/templates") if p.is_dir())


templates = Jinja2Templates(directory=[_TEMPLATES_DIR, *_module_template_dirs()])
