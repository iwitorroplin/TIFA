"""Sesión de login por cookie firmada, sin estado en el servidor: el propio
valor de la cookie lleva el id de usuario más una firma HMAC, así que no hace
falta guardar nada en memoria ni en la base de datos para validarla -solo
comprobar que la firma cuadra con la clave del proceso.

Sin `itsdangerous`/`SessionMiddleware` de Starlette a propósito -sería una
dependencia nueva solo para firmar un entero-; HMAC de la librería estándar
basta para esto.

La clave se genera una vez por proceso (`secrets.token_bytes`, no una
constante fija): reiniciar el servidor cierra todas las sesiones abiertas.
Aceptable para esta primera versión -son unos pocos usuarios sembrados a
mano, no un servicio con usuarios reales esperando seguir conectados-; si
hiciera falta que sobrevivan a un reinicio, la clave pasaría a `web/config.py`.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

COOKIE_NAME = "tifa_session"

_SECRET = secrets.token_bytes(32)


def _firma(user_id: int) -> str:
    mac = hmac.new(_SECRET, str(user_id).encode("ascii"), hashlib.sha256).hexdigest()
    return f"{user_id}.{mac}"


def make_cookie_value(user_id: int) -> str:
    return _firma(user_id)


def verify_cookie_value(value: str | None) -> int | None:
    """El id de usuario si la cookie es válida, o None -cookie ausente,
    manipulada, o firmada por un proceso anterior (clave distinta)."""
    if not value or "." not in value:
        return None
    id_str, _, _mac = value.partition(".")
    if not id_str.isdigit():
        return None
    if not hmac.compare_digest(_firma(int(id_str)), value):
        return None
    return int(id_str)
