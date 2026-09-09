"""Login, logout y la API que los respalda. Sin `Form()` de FastAPI a
propósito -exigiría añadir `python-multipart` como dependencia nueva-: el
formulario de `user_login.html` manda JSON por `fetch`, igual que el resto
de formularios de `web/` (ver `steriflow_lectura.html`).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from web.db import open_conn
from web.modules.user.db import ALL_MODULES, WebUser, get_by_name
from web.modules.user.hashing import verify_password
from web.modules.user.session import COOKIE_NAME, make_cookie_value
from web.templating import templates

router = APIRouter()


class LoginIn(BaseModel):
    name: str
    password: str


def _pagina_de_inicio(usuario: WebUser) -> str:
    """A dónde mandar tras iniciar sesión (o si ya la tenía). Con
    `ALL_MODULES` no hay un único módulo al que ir -`/*` no es una ruta-,
    así que el admin cae en Home, que lista los cuatro."""
    return "/" if usuario.module == ALL_MODULES else f"/{usuario.module}"


@router.get("/login", response_class=HTMLResponse)
def pagina_login(request: Request, next: str = "/") -> HTMLResponse:
    # Ya con sesión: no tiene sentido volver a pedir usuario y contraseña.
    if request.state.user is not None:
        return RedirectResponse(_pagina_de_inicio(request.state.user), status_code=302)
    return templates.TemplateResponse(request, "user_login.html", {"next": next})


@router.post("/api/login")
def procesar_login(datos: LoginIn) -> JSONResponse:
    conn = open_conn()
    try:
        usuario = get_by_name(conn, datos.name)
    finally:
        conn.close()

    # Mismo mensaje tanto si el usuario no existe como si la contraseña no
    # cuadra: decir cuál de las dos falló es un mapa gratis de qué nombres
    # de usuario existen.
    if usuario is None or not verify_password(datos.password, usuario.password_hash, usuario.password_salt):
        return JSONResponse(status_code=401, content={"error": "Usuario o contraseña incorrectos"})

    respuesta = JSONResponse(content={"next": _pagina_de_inicio(usuario)})
    respuesta.set_cookie(COOKIE_NAME, make_cookie_value(usuario.id), httponly=True, samesite="lax")
    return respuesta


@router.get("/logout")
def logout() -> RedirectResponse:
    respuesta = RedirectResponse("/login", status_code=302)
    respuesta.delete_cookie(COOKIE_NAME)
    return respuesta
