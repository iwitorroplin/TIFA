"""Fábrica de la aplicación FastAPI de la parte web.

`create_app()` y no una instancia a nivel de módulo: así cada arranque de
`TifaWebServer.start()` construye una app nueva y limpia, sin arrastrar
estado de un arranque anterior dentro del mismo proceso.
"""

from __future__ import annotations

from typing import Sequence

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.shared.paths import ASSETS_DIR
from web.auth import AccesoDenegado, RequiereLogin, require_login
from web.config import STATIC_DIR
from web.db import open_conn
from web.modules.user.db import ALL_MODULES, get_by_id
from web.modules.user.routes import router as user_router
from web.modules.user.session import COOKIE_NAME, verify_cookie_value
from web.registry import WEB_MODULES
from web.templating import templates


def create_app() -> FastAPI:
    app = FastAPI(title="TIFA Web")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    # Los iconos y retratos de personaje son ficheros compartidos con la app
    # de escritorio (assets/ en la raíz del repo, ni src/ ni web/): se montan
    # tal cual, sin copiarlos.
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    for spec in WEB_MODULES:
        app.include_router(spec.router)
    app.include_router(user_router)

    # La navbar se pinta en templates/base.html a partir de esta misma lista:
    # un módulo nuevo en WEB_MODULES aparece ahí sin tocar ninguna plantilla.
    templates.env.globals["web_modules"] = WEB_MODULES
    # Para que base.html y home.html reconozcan al admin sin hardcodear "*".
    templates.env.globals["ALL_MODULES"] = ALL_MODULES

    @app.middleware("http")
    async def _cargar_usuario(request: Request, call_next):
        """Deja `request.state.user` listo (o en None) antes de que corra
        cualquier dependencia o plantilla -así ambas lo leen sin repetir esta
        lógica cada una por su lado. Se salta /static y /assets: no llevan
        sesión y abrir una conexión a la base de datos por cada CSS/SVG que
        pide una página sería puro desperdicio."""
        request.state.user = None
        if not request.url.path.startswith(("/static/", "/assets/")):
            user_id = verify_cookie_value(request.cookies.get(COOKIE_NAME))
            if user_id is not None:
                conn = open_conn()
                try:
                    request.state.user = get_by_id(conn, user_id)
                finally:
                    conn.close()
        return await call_next(request)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, usuario=Depends(require_login)) -> HTMLResponse:
        return templates.TemplateResponse(request, "home.html", {})

    @app.exception_handler(RequiereLogin)
    async def _requiere_login(request: Request, exc: RequiereLogin):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=401, content={"error": "Inicia sesión"})
        return RedirectResponse(f"/login?next={exc.next_path}", status_code=302)

    @app.exception_handler(AccesoDenegado)
    async def _acceso_denegado(request: Request, exc: AccesoDenegado):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=403, content={"error": "No tienes acceso a este módulo"})
        return HTMLResponse("<h1>403</h1><p>No tienes acceso a este módulo.</p>", status_code=403)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        # JSON para /api/*, HTML simple para el resto -mismo criterio que
        # tenía el servidor anterior sobre http.server.
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})
        return HTMLResponse(f"<h1>{exc.status_code}</h1><p>{exc.detail}</p>", status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": _mensaje_de_error(exc.errors())})

    return app


def _mensaje_de_error(errores: Sequence[dict]) -> str:
    """Un mensaje en castellano a partir del primer fallo de validación de
    Pydantic, en vez de su `msg` en inglés -es lo único de la respuesta que
    la página le enseña a quien está rellenando el formulario."""
    primero = errores[0]
    tipo = primero["type"]
    campo = primero["loc"][-1]
    ctx = primero.get("ctx", {})
    if tipo in ("float_parsing", "float_type", "int_parsing", "int_type"):
        return f"El campo «{campo}» debe ser un número"
    if tipo == "less_than_equal":
        return f"El campo «{campo}» debe ser como mucho {ctx.get('le')}"
    if tipo == "greater_than_equal":
        return f"El campo «{campo}» debe ser como mínimo {ctx.get('ge')}"
    if tipo == "missing":
        return f"Falta el campo «{campo}»"
    return primero.get("msg", "Datos no válidos")
