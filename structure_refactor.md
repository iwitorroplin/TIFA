# TIFA

description: Thermal Integration & F₀ Analysis

---

# Structure

- assets: componentes visuales
- config: configuracion de la app y los modulos
- logs: logs de la app y de los modulos
- data: only for develop, sera la ruta default para los backup y lo que sea necesario
- src: codigo fuente
    - config: codigo para la configuraciond e la app
    - assets: codigo para el manejo de assets

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
- caracters: personajes usados para mandar informacion de log, avisos de procesos, ... 
    - info -> Yufi
    - success -> Tifa
    - warning -> Cloud
    - error -> Sephiroth
- materias: iconos circulares de colores
    -  sustitullen a un icono de un circulo poco estetico
- other: caja desastre lo que aun no tiene suficiente cuerpo como para tener carpeta propia
    - folders



*si renderizado de svg es mucha carga*
*se transformaran los archivos y las rutas para optimizar* 

---

# config: .yaml

separamos 2 carpetas:

**appConfig**: editable y el que leeremos

- appConfig.yaml
- steriflowConfig.yaml
- ferloConfig.yaml
- maconaConfig.yaml
- pasteurizationConfig.yaml

**appConfigDefault**: valores por defecto "si es necesario estaran con los valores en blanco"
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

# src/config

propuesta_optimizacion

- path.py
    - rutas de la configuracion
- manager.py
    - API principal
    - gestion de errores
    - restaurar
    - etc.
- loader.py
    - leer YAML
- writer.py
    - escribir YAML

---

# src/assets

propuesta_optimizacion

- path.py
    - rutas de los assets 

ejemplo:
from src.config.paths import PROJECT_ROOT
ASSETS_DIR = PROJECT_ROOT / "assets"

ICONS_DIR = ASSETS_DIR / "icons"
IMAGES_DIR = ASSETS_DIR / "images"

CHARACTERS_DIR = IMAGES_DIR / "characters"
MATERIAS_DIR = IMAGES_DIR / "materias"
OTHERS_DIR = IMAGES_DIR / "others"
BACKGROUND_DIR = IMAGES_DIR / "background"

*app_logo.svg donde lo añadirias* 


- resources.py
    - los recursos usados (altual assets.py)

---

# REFACTOR IMPORTANTE

**Cambio principal de la estructura**
**Permite Escalar mas comodamente**
**Dudad sobre los mensajes los gestionamos por modulo? algunos son muy distintos**
**Propuesta de mensajes: en module_characters la gestion de mensajes basica y dentro del modulo especificaciones?**
  
src/
│
├── module_home/ (inicio actual modulo home)
│
├── module_characters/ (modulo de control de los caracteres tifa, yufi, cloud, serfirot) 
│
├── module_a/
│   ├── ui/
│   │   ├── dashboard.py
│   │   ├── config.py
│   │   ├── tab_bar.py
│   │   └── components/
│   │       └── ...
│   │
│   ├── logic/
│   ├── utils/
│   └── messages/ ()
|
├── module_b/
│   ├── ui/
│   │   ├── dashboard.py
│   │   ├── config.py
│   │   ├── tab_bar.py
│   │   └── components/
│   │       └── ...
│   │
│   ├── logic/
│   ├── utils/
│   └── messages/
|
└── shared/
│   ├── ui/
|   └── components/
│   ├── logic/
│   ├── utils/
|   ├── messages/
|   ├── components/
|   └── ...
│
└── ...