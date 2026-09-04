# TIFA

description: Thermal Integration & F₀ Analysis

---

# Structure

- assets: componentes visuales
- config: configuracion de la app y los modulos (`appConfig/` real, `appConfigDefault/` versionado)
- logs: logs de la app y de los modulos
- data: only for develop, sera la ruta default para los backup y lo que sea necesario
- src: codigo fuente
    - app: cascaron de la app (MainWindow, Navbar, TrayApp) — ni modulo ni shared
    - modules: un paquete por modulo de negocio
    - shared: todo lo transversal a los modulos

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
- `logs/`: `logger.py`, `files.py`, `history.py` (genericos, parametrizados por prefijo de fichero)
- `messages/`: `types.py` (`MessageType`, `Module`, `Delivery`), `message.py`, `manager.py` — que se dice y quien lo origina
- `characters/`: `senders.py`, `portrait.py`, `message_box.py`, `message_bar.py` — quien lo dice y como se ve; descarta los mensajes `Delivery.SILENT` antes de mostrar personaje/popup
- `ui/`: `formatting.py` + `components/` (botones, tab bar, barras de carga, tail de log)
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

El cascaron de la aplicacion: `window_app.py` (`MainWindow`), `nav_bar.py` (`Navbar`), `tray_app.py` (`TrayApp`). Construyen la ventana a partir de `src.modules.registry.MODULES`, sin conocer a ningun modulo por su nombre.

---

# Herramientas

`tools/check_imports.py`: importa cada modulo bajo `src/` y reporta cualquier fallo. No hay tests en el repo; es la unica red de seguridad ante una refactorizacion o un movimiento de ficheros.
