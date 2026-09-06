"""Ajustes del servidor web. Constantes, no YAML: son valores que se cambian
una vez en la vida; no justifican el patrón de config de `src/shared/config/`
(default versionado + copia editable + dataclass) para esto. El día que haga
falta configurarlo desde la app, `TifaWebServer` ya recibe host/puerto por
parámetro (ver `web/server.py`) y aquí solo cambiarían los valores por defecto.
"""

from __future__ import annotations

from pathlib import Path

# "0.0.0.0": todas las interfaces de red, para que otros PC de la LAN lleguen.
# Con "127.0.0.1" solo se vería desde este mismo ordenador.
HOST = "0.0.0.0"
PORT = 8000

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Límites de saneo para los listados (`GET /api/<modulo>?limit=`), compartidos
# entre módulos para no repetir el mismo par de números en cada routes.py.
DEFAULT_LIMIT = 20
MAX_LIMIT = 200
