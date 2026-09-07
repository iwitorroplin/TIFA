"""Usuarios de prueba, uno por módulo, para no depender de un formulario de
alta que no existe todavía (`web/modules/user/routes.py` solo tiene login).

Contraseñas de usar-y-cambiar, no de producción: sirven para probar el
circuito de acceso por módulo (cada usuario solo ve el suyo), no para
proteger nada de verdad. Cámbialas -o siembra las tuyas- antes de dejar el
servidor accesible a nadie fuera de pruebas.
"""

from __future__ import annotations

import sqlite3

from web.modules.user.db import create_user, get_by_name
from web.modules.user.hashing import hash_password

# (nombre, contraseña, módulo)
_USUARIOS_SEMILLA = [
    ("steriflow", "steriflow123", "steriflow"),
    ("ferlo", "ferlo123", "ferlo"),
    ("macona", "macona123", "macona"),
    ("pasteurization", "pasteurization123", "pasteurization"),
]


def seed_default_users(conn: sqlite3.Connection) -> list[str]:
    """Crea los usuarios semilla que falten. Idempotente: si el nombre ya
    existe no lo toca. Devuelve los nombres realmente creados. No hace
    commit -cosa del llamante, ver seed_web_users.py-."""
    creados = []
    for name, password, module in _USUARIOS_SEMILLA:
        if get_by_name(conn, name) is not None:
            continue
        password_hash, password_salt = hash_password(password)
        create_user(conn, name, password_hash, password_salt, module)
        creados.append(name)
    return creados
