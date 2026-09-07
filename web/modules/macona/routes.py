"""Macona todavía no tiene lógica propia en la parte web -igual que
`src/modules/macona` tampoco la tiene en la app de escritorio. Este router
solo reserva su sitio en la navbar; cuando exista un `macona_web` real, se le
añade `/api/macona` y un `db.py`, siguiendo el patrón de
`web/modules/steriflow/`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from web.auth import require_module
from web.modules.user.db import WebUser
from web.templating import templates

router = APIRouter()


@router.get("/macona", response_class=HTMLResponse)
def pagina(request: Request, usuario: WebUser = Depends(require_module("macona"))) -> HTMLResponse:
    return templates.TemplateResponse(request, "proximamente.html", {"modulo": "Macona"})
