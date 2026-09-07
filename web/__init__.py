"""Sistema web de TIFA: la cara de la app hacia los usuarios de fuera.

`src/` es la app de escritorio. Esto es otra cosa -otro proceso, otro
protocolo de entrada (HTTP en vez de Qt), pensado para que alguien meta un
dato desde su propio ordenador o su móvil sin tener TIFA instalada-. Están
relacionados (comparten el mismo `data/tifa.db`) pero no son lo mismo ni
funcionan igual, y por eso viven en carpetas distintas en vez de colgar `web/`
de `src/modules/`.

Regla de dependencia: **`web/` no importa nada de `src/modules/`**. Lo único
que se comparte con la app de escritorio es la fontanería de
`src/shared/db/` (conexión, registro de esquema, formato de fechas) -tres
ficheros sin Qt y sin lógica de negocio de ningún módulo concreto-. El
esquema, el repositorio y el log de la parte web son propios de este paquete
(`web/db.py`, `web/log.py`).

Construido sobre FastAPI + Uvicorn, y organizado en `web/modules/<nombre>/`
igual que `src/modules/`: cada módulo de negocio (steriflow, ferlo, macona,
pasteurization) agrupa sus rutas, su tabla `*_web` (si la tiene) y su propia
plantilla, y `web/registry.py` es el único fichero con permiso para
conocerlos a todos a la vez -mismo papel que cumple `src/modules/registry.py`
en la app de escritorio, sin relación alguna entre ambos.

Se ejecuta con `python run_web.py` desde la raíz del repo, como proceso
aparte de `python run_app.py`.
"""
