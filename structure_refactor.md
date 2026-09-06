# TIFA

description: Thermal Integration & F₀ Analysis

---

# Structure

- assets: componentes visuales
- config: configuracion de la app y los modulos (`appConfig/` real, `appConfigDefault/` versionado)
- logs: logs de la app y de los modulos
- data: only for develop, sera la ruta default para los backup y lo que sea necesario
- src: codigo fuente de la app de escritorio
    - app: cascaron de la app (MainWindow, Navbar, TrayApp) — ni modulo ni shared
    - modules: un paquete por modulo de negocio
    - shared: todo lo transversal a los modulos
- web: sistema de cara a los usuarios de fuera (servidor HTTP para la LAN); otro proceso, no cuelga de src/

**future features**

---

# assets: .ico and .svg

**icons** : only file .ico
- dedicado para los iconos de
    - app
    - tray
    - ui
    - window
- por ahroa el archvio es e mismo para todo 

**images** : only file .svg and png
- background:
    - dado que la imagen es muy detallada e renderizado es lento se usa .png
- characters: personajes usados para mandar informacion de log, avisos de procesos, ...
    - info -> Yufi
    - success -> Tifa
    - warning -> Cloud
    - error -> Sephiroth
- materias: iconos circulares de colores
    -  sustitullen a un icono de un circulo poco estetico
- other: caja desastre lo que aun no tiene suficiente cuerpo como para tener carpeta propia
    - folders

---

# config: .yaml

separamos 2 carpetas:

**appConfig**: editable y el que leeremos (sin versionar, `.gitignore` ignora la carpeta entera)

- appConfig.yaml
- steriflowConfig.yaml
- ferloConfig.yaml
- maconaConfig.yaml
- pasteurizationConfig.yaml

**appConfigDefault**: valores por defecto, versionados; la app copia el que falte a `appConfig/` la primera vez que se ejecuta
- appConfig.default.yaml
- steriflowConfig.default.yaml
- ferloConfig.default.yaml
- maconaConfig.default.yaml
- pasteurizationConfig.default.yaml

---

# data

archivos de la base de datos

por ahora solo tifa.db
se añadiran si es necesario

---

# src/shared

Todo lo transversal a los modulos, para que ninguno tenga que reinventarlo:

- `paths.py`: unico ancla `PROJECT_ROOT` del proyecto (antes duplicada como `parents[N]` en cinco sitios distintos)
- `assets/`: `paths.py` (carpetas) + `resources.py` (constantes de icono/imagen)
- `config/`: `paths.py`, `loader.py`, `writer.py`, `manager.py` (`ensure_config_file`, `load_config`, `save_config`, `restore_defaults`), `app_config.py`
- `db/`: `connection.py` + `schema.py` (registro `register_schema`/`ensure_schema` — no conoce a ningun modulo) + `iso.py`
- `logs/`: `logger.py` (escribe el historial; `talk=` opcional para que ademas hable un personaje), `files.py`, `history.py` (genericos, parametrizados por prefijo de fichero), `retention.py` (borra los logs mas viejos que los meses configurados en appConfig)
- `messages/`: `types.py` (`MessageType`, `Module`), `message.py`, `manager.py` — bus de avisos inmediatos: que se dice y quien lo origina, sin historial (el historial son los logs)
- `characters/`: `senders.py`, `portrait.py`, `message_box.py`, `message_bar.py` — quien lo dice y como se ve; INFO/SUCCESS se cierran solos, WARNING/ERROR esperan al OK
- `ui/`: `formatting.py` + `printing.py` (impresion y PDF: tablas, texto e imagenes sobre QTextDocument, que pagina solo) + `components/` (botones, tab bar, barras de carga, tail de log)
- `utils/folders.py`

---

# src/modules

Un paquete por modulo, cada uno con su propio corte vertical:

```
src/modules/<modulo>/
├── ui/          vistas, tab bar, paginas propias del modulo
├── logic/       reglas de negocio, config, acceso a datos del modulo
├── utils/       utilidades que no encajan en shared/ por ser especificas del modulo
└── messages/    catalogo de textos que emite el modulo via shared/messages
```

Steriflow es el unico modulo con contenido real (`logic/` con backup, sterilization, scheduler, config propia; `ui/` con sus 4 pestañas). Home, Ferlo, Macona, Pasteurizacion, Config, Logs y Prueba UI son esqueletos con `ui/view.py`.

`src/modules/registry.py` es el **composition root**: la unica lista (`MODULES: list[ModuleSpec]`) de la que Navbar y MainWindow generan sus botones/paginas en el mismo orden, y de la que `__main__.py` registra el esquema de base de datos de cada modulo. Ningun modulo importa `registry.py` — evita el ciclo con el propio modulo que el registro ensambla.

---

# src/app

El cascaron de la aplicacion: `window_app.py` (`MainWindow`), `nav_bar.py` (`Navbar`), `tray_app.py` (`TrayApp`), `housekeeping.py` (limpieza de logs viejos y registro de fallos no controlados, al arrancar). Construyen la ventana a partir de `src.modules.registry.MODULES`, sin conocer a ningun modulo por su nombre.

---

# web

Sistema de TIFA de cara a los usuarios de fuera: un servidor web (FastAPI + Uvicorn) pensado para que alguien meta un dato desde otro ordenador de la red local o desde su movil, sin tener TIFA instalada. Es otro proceso (`python run_web.py`), no una vista mas de `src/`.

Relacionado con `src/` pero no es lo mismo: **`web/` no importa nada de `src/modules/`**. Lo unico que comparte con la app de escritorio es la base de datos (`data/tifa.db`) y para eso reutiliza la fontaneria de `src/shared/db/` (conexion, registro de esquema, formato de fechas). El esquema, el repositorio y el log de la parte web son propios, organizados por modulo igual que `src/modules/`:

```
web/
├── app.py        create_app() -> FastAPI: monta /static y /assets, middleware de sesion, routers, plantillas
├── auth.py       require_login / require_module(id) — control de acceso, compartido por todos los modulos
├── registry.py   WEB_MODULES: list[WebModuleSpec] — composition root (mirror de src/modules/registry.py)
├── server.py     TifaWebServer (start/stop/wait_forever), envuelve uvicorn.Server en un hilo daemon
├── config.py     host/puerto/limites (constantes, no YAML)
├── db.py         open_conn() -> delega en src.shared.db.connection.connect
├── log.py        log a fichero sin Qt (Logger de shared/logs arrastra PySide6)
├── templating.py Jinja2Templates compartido (busca en web/templates/ + cada modules/<x>/templates/)
├── templates/    base.html (layout: sidebar + banner de aviso), home.html, proximamente.html, _tab_bar.html (macro)
├── static/       style.css + portrait.js, compartidos
└── modules/
    ├── steriflow/       routes.py (APIRouter), schemas.py (Pydantic), db.py (DDL+modelo+repo), templates/
    ├── ferlo/           routes.py — placeholder, sin tabla propia aun
    ├── macona/          idem
    ├── pasteurization/  idem
    └── user/            login: db.py (tabla web_user), hashing.py, session.py (cookie firmada), seed.py, routes.py, templates/
```

Tablas nuevas con sufijo `_web` (una por modulo de negocio), cada una definida en el `db.py` de su propio `web/modules/<x>/`. Por ahora solo `steriflow_web` existe; los otros tres modulos estan registrados en la navbar pero sin tabla ni API todavia.

**Acceso por usuario** (`web/modules/user/` + `web/auth.py`): tabla `web_user` (id, name, password_hash+password_salt, module, created_at) — cada usuario tiene exactamente un modulo asignado. Sin formulario de alta: se siembran con `python seed_web_users.py` (idempotente, ver `web/modules/user/seed.py`). Login por cookie firmada con HMAC (sin `itsdangerous`/`SessionMiddleware`, cero dependencias nuevas); la clave se genera por proceso, así que reiniciar el servidor cierra las sesiones. Cada ruta de un modulo se protege con `Depends(require_module("<id>"))`; sin sesion redirige a `/login` (o 401 JSON si es `/api/*`), con sesion pero modulo distinto da 403. La navbar solo pinta el modulo asignado al usuario -no los cuatro-, así que la restriccion de acceso también es la propia navegación.

**Estructura visual**, calcada de `src/app/` en HTML/CSS/JS (no en codigo: `nav_button.py`, `tab_bar.py`, `message_bar.py`, `senders.py` y `portrait.py` son Qt puro, no se pueden importar en `web/`):

- **Navbar vertical** por modulo (`templates/base.html`), un boton por `WebModuleSpec` igual que `Navbar` en `src/app/nav_bar.py` — colapsa a barra horizontal en movil (media query en `static/style.css`), a diferencia del escritorio.
- **Tab bar** horizontal dentro de un modulo (macro `templates/_tab_bar.html`), equivalente a `TabBar`; cada pestaña es una URL propia (`/steriflow`, `/steriflow/lectura`, `/steriflow/historial`), no un cambio de estado por JS.
- **Aviso con personaje** (`static/portrait.js`), equivalente web de `MessageBar`/`MessageBox`: reutiliza los SVG de personaje de `assets/images/characters/` (montados en `/assets`, ver `web/app.py`) y repite en JS el mismo truco de teñido de `portrait.py` (sustituir `fill:#ffffff` por el color de acento). A diferencia del escritorio no hay bus de mensajes en vivo entre modulos (eso pedira WebSockets, fuera de alcance): solo reacciona a la propia accion que esa pagina acaba de hacer.

Convencion de nombres de plantilla: cada modulo prefija las suyas con su propio nombre (`steriflow_inicio.html`, no `inicio.html`) — Jinja2 busca en `web/templates/` y en cada `modules/<x>/templates/` como una sola lista, y dos ficheros con el mismo nombre en dos carpetas se taparian en silencio sin el prefijo.

`TifaWebServer.start()`/`stop()`/`wait_forever()` no cambian aunque cambie el motor de dentro (paso de `http.server` a Uvicorn sin tocar `run_web.py`): sirve igual para `run_web.py` que para un futuro interruptor en la UI de TIFA.

---

# Herramientas

`tools/check_imports.py`: importa cada modulo bajo `src/` y `web/` y reporta cualquier fallo. No hay tests en el repo; es la unica red de seguridad ante una refactorizacion o un movimiento de ficheros.
