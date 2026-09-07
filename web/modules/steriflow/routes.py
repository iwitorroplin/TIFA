"""Rutas de Steriflow en la parte web: la página del formulario y su API."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from web.auth import require_module
from web.config import DEFAULT_LIMIT, MAX_LIMIT
from web.db import open_conn
from web.modules.steriflow.db import SteriflowReading, list_readings, save_reading
from web.modules.steriflow.schemas import SteriflowReadingIn, SteriflowReadingOut
from web.modules.user.db import WebUser
from web.templating import templates

router = APIRouter()

# Una sola instancia: la misma dependencia se repite en las 5 rutas de abajo,
# páginas y API, para que a ninguna se le olvide exigir el módulo.
_requiere_steriflow = require_module("steriflow")


@router.get("/steriflow", response_class=HTMLResponse)
def pagina_inicio(request: Request, usuario: WebUser = Depends(_requiere_steriflow)) -> HTMLResponse:
    return templates.TemplateResponse(request, "steriflow_inicio.html", {})


@router.get("/steriflow/lectura", response_class=HTMLResponse)
def pagina_lectura(request: Request, usuario: WebUser = Depends(_requiere_steriflow)) -> HTMLResponse:
    # created_by ya relleno con quien ha entrado: no hay que teclear el
    # nombre en cada lectura, solo cambiarlo si de verdad la manda otra persona.
    return templates.TemplateResponse(request, "steriflow_lectura.html", {"usuario": usuario})


@router.get("/steriflow/historial", response_class=HTMLResponse)
def pagina_historial(request: Request, usuario: WebUser = Depends(_requiere_steriflow)) -> HTMLResponse:
    return templates.TemplateResponse(request, "steriflow_historial.html", {})


@router.get("/api/steriflow", response_model=list[SteriflowReadingOut])
def listar(
    usuario: WebUser = Depends(_requiere_steriflow),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> list[SteriflowReading]:
    conn = open_conn()
    try:
        return list_readings(conn, limit=limit)
    finally:
        conn.close()


@router.post("/api/steriflow", response_model=SteriflowReadingOut, status_code=201)
def crear(datos: SteriflowReadingIn, usuario: WebUser = Depends(_requiere_steriflow)) -> SteriflowReading:
    reading = SteriflowReading(
        temp_c=datos.temp_c, created_by=datos.created_by, note=datos.note,
        created_at=dt.datetime.now(),
    )
    conn = open_conn()
    try:
        reading.id = save_reading(conn, reading)
        conn.commit()
    finally:
        conn.close()
    return reading
