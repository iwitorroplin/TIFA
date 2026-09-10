"""
Genera el ejecutable de la app de escritorio:

    python run_create_exe.py

Deja en `dist/TIFA/` la carpeta lista para copiar a la máquina destino:
`TIFA.exe` con el intérprete y las librerías dentro, y al lado `assets/` y
`config/appConfigDefault/`.

Carpeta y no ejecutable único (--onefile): `src/shared/paths.py` calcula
PROJECT_ROOT desde `sys.executable` cuando está congelado, así que assets,
config, la base de datos y los logs se buscan JUNTO al .exe, no dentro del
temporal que --onefile descomprime en cada arranque. Empaquetarlo de una
pieza dejaría a la app leyendo una copia que se borra al cerrar -y perdiendo
los datos escritos-.

`config/appConfig/` no se copia a propósito: es la configuración que el
usuario edita desde la app, y `src/shared/config/manager.py` la crea sola a
partir de los `.default.yaml` la primera vez que no existe. Copiarla aquí
plantaría en destino la configuración de la máquina de desarrollo.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

APP_NAME = "TIFA"
ENTRY_POINT = PROJECT_ROOT / "run_app.py"
ICON = PROJECT_ROOT / "assets" / "icons" / "app.ico"

BUILD_DIR = PROJECT_ROOT / "build" / "pyinstaller"
DIST_DIR = PROJECT_ROOT / "dist"
OUTPUT_DIR = DIST_DIR / APP_NAME

# Carpetas que la app lee en tiempo de ejecución desde PROJECT_ROOT: se
# copian al lado del .exe en vez de ir dentro del paquete (--add-data), que
# las metería en `_internal/` donde paths.py no las busca.
DATA_FOLDERS = [
    Path("assets"),
    Path("config") / "appConfigDefault",
]

# pyqtgraph y pdfplumber arrastran importaciones que el análisis estático de
# PyInstaller no siempre ve; sin esto el fallo aparece tarde, ya en destino y
# solo al abrir la curva del ciclo o al leer un PDF.
HIDDEN_IMPORTS = [
    "pyqtgraph",
    "pdfplumber",
]

# El servidor web (web/) es un proceso aparte: no entra en este ejecutable.
EXCLUDES = [
    "fastapi",
    "uvicorn",
    "tkinter",
    "pytest",
]


def _check_prerequisites() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit(
            "Falta PyInstaller. Instálalo con:\n"
            "    python -m pip install pyinstaller"
        )

    if not ENTRY_POINT.exists():
        sys.exit(f"No encuentro el punto de entrada: {ENTRY_POINT}")

    for folder in DATA_FOLDERS:
        if not (PROJECT_ROOT / folder).is_dir():
            sys.exit(f"No encuentro la carpeta a copiar: {folder}")


def _build_command() -> list[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ENTRY_POINT),
        "--name",
        APP_NAME,
        # Sin consola detrás de la ventana: es una app de escritorio. Si algo
        # revienta al arrancar, el rastro queda en data/logs/tifa.log gracias
        # al manejador de src/app/housekeeping.py.
        "--windowed",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
    ]

    if ICON.exists():
        command += ["--icon", str(ICON)]

    for module in HIDDEN_IMPORTS:
        command += ["--hidden-import", module]

    for module in EXCLUDES:
        command += ["--exclude-module", module]

    return command


def _copy_runtime_folders() -> None:
    for folder in DATA_FOLDERS:
        source = PROJECT_ROOT / folder
        target = OUTPUT_DIR / folder
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        print(f"  copiado  {folder}")


def main() -> None:
    _check_prerequisites()

    print(f"Empaquetando {APP_NAME} desde {ENTRY_POINT.name}...")
    result = subprocess.run(_build_command(), cwd=PROJECT_ROOT)
    if result.returncode != 0:
        sys.exit(f"PyInstaller falló (código {result.returncode}).")

    print("Copiando carpetas de tiempo de ejecución:")
    _copy_runtime_folders()

    print(f"\nListo: {OUTPUT_DIR}\\{APP_NAME}.exe")
    print(
        "Para distribuir, copia la carpeta entera: el .exe solo no arranca "
        "sin assets/ y config/ al lado."
    )


if __name__ == "__main__":
    main()
