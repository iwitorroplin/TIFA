"""Hash de contraseñas de `web_user`.

PBKDF2-HMAC-SHA256 de la librería estándar -sin dependencias nuevas, mismo
criterio que el resto de `web/`-, con una sal aleatoria por usuario para que
dos contraseñas iguales no guarden el mismo hash.
"""

from __future__ import annotations

import hashlib
import hmac
import os

_ITERACIONES = 200_000


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Devuelve (hash_hex, salt_hex).

    Sin `salt`: genera una nueva sal, para dar de alta una contraseña.
    Con `salt`: usa la ya guardada, para comprobar una contraseña existente
    -ver `verify_password`-.
    """
    salt = salt if salt is not None else os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERACIONES)
    return derivado.hex(), salt.hex()


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    calculado, _ = hash_password(password, bytes.fromhex(password_salt))
    # compare_digest y no `==`: evita que el tiempo de comparación filtre
    # cuántos caracteres del hash acertó un intento.
    return hmac.compare_digest(calculado, password_hash)
