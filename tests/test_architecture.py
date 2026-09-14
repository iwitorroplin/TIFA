"""Guardián de arquitectura: ningún fichero de `logic/` puede importar Qt ni
nada de `ui/`.

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


def _imports(path: Path) -> list[str]:
    """Los módulos que importa `path`, también los de dentro de un
    `if TYPE_CHECKING:` -`ast.walk` recorre todo el árbol-, que es justo
    donde una dependencia hacia `ui/` se cuela sin que falle nada al
    ejecutar. Los relativos conservan sus puntos (`..ui.x`)."""
    arbol = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    encontrados: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            encontrados.extend(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            encontrados.append("." * nodo.level + (nodo.module or ""))
    return encontrados


def _es_qt(modulo: str) -> bool:
    return modulo.startswith(_QT_PREFIXES)


def _es_ui(modulo: str) -> bool:
    return "ui" in modulo.lstrip(".").split(".")


def _ofensores(logic_dir: Path, prohibido) -> dict[str, list[str]]:
    return {
        str(py_file.relative_to(PROJECT_ROOT)): culpables
        for py_file in logic_dir.rglob("*.py")
        if (culpables := [m for m in _imports(py_file) if prohibido(m)])
    }


@pytest.mark.parametrize("logic_dir", LOGIC_DIRS, ids=lambda p: p.parent.name)
def test_logic_no_importa_qt(logic_dir: Path):
    ofensores = _ofensores(logic_dir, _es_qt)
    assert not ofensores, f"logic/ no puede importar Qt (ver docstring del test): {ofensores}"


@pytest.mark.parametrize("logic_dir", LOGIC_DIRS, ids=lambda p: p.parent.name)
def test_logic_no_importa_ui(logic_dir: Path):
    """La dependencia va de `ui/` hacia `logic/`, nunca al revés: si el
    dominio necesita algo de la interfaz, ese algo está mal ubicado (así pasó
    con las celdas de `steriflow/logic/sterilization/columns.py`, que se
    tipaban contra el view model de la tabla)."""
    ofensores = _ofensores(logic_dir, _es_ui)
    assert not ofensores, f"logic/ no puede importar de ui/ (ver docstring del test): {ofensores}"


def test_hay_al_menos_un_modulo_con_logic():
    """Si esto falla, `LOGIC_DIRS` está vacío y el test de arriba pasaría
    por no tener nada que comprobar -una regresión silenciosa del propio
    guardián, no del código que vigila."""
    assert LOGIC_DIRS
