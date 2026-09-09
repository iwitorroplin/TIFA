"""Guardián de arquitectura: ningún fichero de `logic/` puede importar Qt.

Portado del origen de Ferlo (`sterilization_analysis`, que traía un test así
para su propio `core/`): barato, y es lo único que impide que dentro de seis
meses alguien meta un `QMessageBox` dentro de una función de dominio y deje
esa lógica sin poder probarse sin abrir una ventana (ver el plan de
integración de Ferlo, sección 04 "Dónde puede torcerse").

Analiza el CÓDIGO FUENTE con `ast` en vez de importar cada módulo: así corre
igual de rápido con o sin pantalla, y no depende de que cada fichero de
`logic/` sea importable de forma aislada (algunos solo tienen sentido dentro
de su paquete).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGIC_DIRS = sorted((PROJECT_ROOT / "src" / "modules").glob("*/logic"))

_QT_PREFIXES = ("PySide6", "PyQt5", "PyQt6", "pyqtgraph")


def _qt_imports(path: Path) -> list[str]:
    arbol = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    encontrados: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            encontrados.extend(
                alias.name for alias in nodo.names if alias.name.startswith(_QT_PREFIXES)
            )
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            if nodo.module.startswith(_QT_PREFIXES):
                encontrados.append(nodo.module)
    return encontrados


@pytest.mark.parametrize("logic_dir", LOGIC_DIRS, ids=lambda p: p.parent.name)
def test_logic_no_importa_qt(logic_dir: Path):
    ofensores = {
        str(py_file.relative_to(PROJECT_ROOT)): culpables
        for py_file in logic_dir.rglob("*.py")
        if (culpables := _qt_imports(py_file))
    }
    assert not ofensores, f"logic/ no puede importar Qt (ver docstring del test): {ofensores}"


def test_hay_al_menos_un_modulo_con_logic():
    """Si esto falla, `LOGIC_DIRS` está vacío y el test de arriba pasaría
    por no tener nada que comprobar -una regresión silenciosa del propio
    guardián, no del código que vigila."""
    assert LOGIC_DIRS
