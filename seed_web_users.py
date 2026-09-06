"""Siembra usuarios de prueba en `web_user`, uno por módulo (ver
`web/modules/user/seed.py` para las credenciales exactas):

python seed_web_users.py

Idempotente: si un usuario ya existe (mismo nombre), no lo toca -se puede
ejecutar tantas veces como haga falta.
"""

from web.db import open_conn
from web.modules.user.seed import seed_default_users


def main() -> None:
    conn = open_conn()
    try:
        creados = seed_default_users(conn)
        conn.commit()
    finally:
        conn.close()

    if not creados:
        print("Nada que sembrar: los usuarios de prueba ya existían.")
        return
    for nombre in creados:
        print(f"Usuario creado: {nombre}")


if __name__ == "__main__":
    main()
