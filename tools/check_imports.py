"""Importa cada módulo bajo src/ y reporta cualquier fallo.

Guardián de la refactorización: no requiere Qt en pantalla ni base de datos
real, solo detecta imports rotos, ciclos y rutas de paquete equivocadas.

Uso: python tools/check_imports.py
"""

from __future__ import annotations

import pkgutil
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import src  # noqa: E402


def main() -> int:
    failures: list[tuple[str, BaseException]] = []
    modules = sorted(
        name
        for _, name, _ in pkgutil.walk_packages(src.__path__, prefix="src.")
    )
    for name in modules:
        try:
            __import__(name)
        except Exception as exc:  # noqa: BLE001
            failures.append((name, exc))

    print(f"{len(modules)} módulos comprobados.")
    if not failures:
        print("OK: ningún import roto.")
        return 0

    print(f"\n{len(failures)} módulo(s) con error de import:\n")
    for name, exc in failures:
        print(f"--- {name} ---")
        traceback.print_exception(type(exc), exc, exc.__traceback__)
        print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
