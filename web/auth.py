"""Control de acceso, compartido por todos los módulos -no es un módulo de
negocio más, es fontanería como `web/db.py` o `web/templating.py`. Por eso
vive suelto en `web/` y no dentro de `web/modules/user/`: si viviera ahí,
cada módulo tendría que importar "del módulo de otro" para protegerse, que es
justo lo que la arquitectura de `web/modules/` evita entre módulos de negocio.

Cada ruta de un módulo se protege añadiendo un parámetro con
`Depends(require_module("<id>"))` (o `Depends(require_login)` para páginas
que no son de ningún módulo en concreto, como Home). Las dos excepciones las
traduce `web/app.py` a una redirección a `/login` o a un 403, según si quien
pregunta es una página o la API -ver sus manejadores en `create_app()`.
"""

from __future__ import annotations

from fastapi import Request

from web.modules.user.db import ALL_MODULES, WebUser


class RequiereLogin(Exception):
    """No hay sesión válida. `next_path` es a dónde volver tras iniciar
    sesión, para no dejar a quien entra tirado en Home."""

    def __init__(self, next_path: str) -> None:
        self.next_path = next_path


class AccesoDenegado(Exception):
    """Hay sesión, pero el módulo pedido no es el suyo."""


def require_login(request: Request) -> WebUser:
    if request.state.user is None:
        raise RequiereLogin(request.url.path)
    return request.state.user


def require_module(module_id: str):
    """Fábrica de dependencia: `Depends(require_module("steriflow"))` en cada
    ruta de ese módulo -página o API- exige sesión Y que sea justo ese
    módulo el asignado al usuario -o que tenga `ALL_MODULES` (admin)-."""

    def dependencia(request: Request) -> WebUser:
        usuario = require_login(request)
        if usuario.module != module_id and usuario.module != ALL_MODULES:
            raise AccesoDenegado()
        return usuario

    return dependencia
