"""Ingesta de informes Steriflow.

Recorre la carpeta de cada autoclave activo y guarda un ciclo por PDF. No hay
etapa de analisis: lo que la maquina imprime es lo que se guarda.

Va en dos fases -primero listar, luego leer- porque listar es practicamente
gratis y leer no: sabiendo el total por adelantado se puede informar del avance
("137/2000") en vez de dejar la interfaz en un "importando…" de once minutos.

Un informe ya guardado se descarta SIN abrirlo, por el instante que lleva su
propio nombre (ver `_ya_importado`). Es la diferencia entre reimportar una
carpeta de 2.000 informes en 0,1 segundos o en 11 minutos.

Este modulo no importa Qt: el progreso y la cancelacion entran como callables
corrientes, y es `ui/panel.py` quien los conecta a la ventana.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..core.config import Settings, SteriflowAutoclave
from ..io.base import sha256_of
from .models import SteriflowCycle
from .reader import SteriflowReadError, read_report, started_at_from_filename
from .repo import SteriflowCycleRow, find_by_sha, known_start_times, save_cycle
from .schema import ensure_tables

# La maquina deja aqui los informes que ella misma descarta: no son ciclos
# validos y no deben entrar en la base de datos.
CARPETAS_EXCLUIDAS = {"export_no_valid"}

# (hechos, total, etiqueta) -> None
OnProgress = Callable[[int, int, str], None]
ShouldCancel = Callable[[], bool]


@dataclass(slots=True)
class SteriflowIngestResult:
    autoclave: SteriflowAutoclave
    folder: Path
    cycles_new: int = 0
    cycles_updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    folder_missing: bool = False
    cancelled: bool = False

    @property
    def read_count(self) -> int:
        return self.cycles_new + self.cycles_updated


def discover_reports(folder: Path, pattern: str = "*.pdf") -> list[Path]:
    """PDF de una carpeta de autoclave, sin recursion.

    Sin recursion a proposito: dentro de cada AUTOCLAVE<n> cuelga
    `Export_No_Valid`, y un glob recursivo se traeria justo lo que la maquina ha
    descartado.
    """
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.glob(pattern)
        if p.is_file() and p.parent.name.casefold() not in CARPETAS_EXCLUIDAS
    )


def report_folder(settings: Settings, autoclave_code: int) -> Path:
    """Carpeta donde deberian estar los informes de un autoclave.

    Un codigo que ya no este en la configuracion -se quito el autoclave, pero
    sus ciclos siguen en la base de datos- cae en la carpeta que la maquina usa
    por defecto, AUTOCLAVE<code>.
    """
    root = settings.steriflow_reports_root
    for autoclave in settings.steriflow_autoclaves:
        if autoclave.code == autoclave_code:
            return autoclave.resolve_folder(root)
    return SteriflowAutoclave(code=autoclave_code, name="").resolve_folder(root)


def report_path(
    settings: Settings, cycle: SteriflowCycleRow | SteriflowCycle
) -> Path | None:
    """Ruta del PDF del que salio un ciclo guardado, o None si ya no esta.

    De cada ciclo se guarda el NOMBRE del fichero, no su ruta: la ruta se
    recompone con la carpeta que tenga hoy ese autoclave. Asi, mover la raiz de
    informes en Configuracion se lleva con ella todo el historico; a cambio, un
    informe archivado fuera de su carpeta deja de encontrarse.

    Si el nombre no da con el fichero -se renombro a mano-, se busca en la
    carpeta por el instante de arranque, que es la identidad del ciclo y va en
    el propio nombre (ver `reader.started_at_from_filename`).
    """
    carpeta = report_folder(settings, cycle.autoclave_code)
    directa = carpeta / cycle.source_filename
    if directa.is_file():
        return directa

    patron = settings.steriflow.get("file_pattern", "*.pdf")
    for ruta in discover_reports(carpeta, patron):
        if started_at_from_filename(ruta) == cycle.started_at:
            return ruta
    return None


def plan_ingest(
    settings: Settings, *, pattern: str | None = None
) -> list[tuple[SteriflowAutoclave, Path, list[Path]]]:
    """Que hay que leer, sin leer nada todavia: (autoclave, carpeta, ficheros).

    Solo listados de directorio, asi que cuesta milisegundos incluso con miles
    de informes. De aqui sale el total que necesita la barra de progreso.
    """
    root = settings.steriflow_reports_root
    patron = pattern or settings.steriflow.get("file_pattern", "*.pdf")
    plan = []
    for autoclave in settings.steriflow_autoclaves:
        if not autoclave.is_active:
            continue
        carpeta = autoclave.resolve_folder(root)
        plan.append((autoclave, carpeta, discover_reports(carpeta, patron)))
    return plan


def ingest_all(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    force: bool = False,
    on_progress: OnProgress | None = None,
    should_cancel: ShouldCancel | None = None,
) -> list[SteriflowIngestResult]:
    """Importa los informes de todos los autoclaves Steriflow activos.

    `should_cancel` se consulta antes de cada fichero: cancelar deja lo ya
    importado en la base de datos -cada ciclo se confirma por separado- y marca
    `cancelled` en el resultado en curso.
    """
    ensure_tables(conn)
    plan = plan_ingest(settings)
    total = sum(len(ficheros) for _, _, ficheros in plan)

    resultados: list[SteriflowIngestResult] = []
    hechos = 0
    for autoclave, carpeta, ficheros in plan:
        resultado = SteriflowIngestResult(
            autoclave=autoclave, folder=carpeta, folder_missing=not carpeta.is_dir()
        )
        resultados.append(resultado)
        if resultado.folder_missing:
            continue

        conocidos = known_start_times(conn, autoclave.code)
        for ruta in ficheros:
            if should_cancel is not None and should_cancel():
                resultado.cancelled = True
                return resultados
            hechos += 1
            if on_progress is not None:
                on_progress(hechos, total, f"{autoclave.name} · {ruta.name}")
            _ingest_one(conn, autoclave, ruta, conocidos, resultado, force=force)
    return resultados


def ingest_autoclave(
    conn: sqlite3.Connection,
    autoclave: SteriflowAutoclave,
    root: Path,
    *,
    pattern: str = "*.pdf",
    force: bool = False,
) -> SteriflowIngestResult:
    """Importa los informes de un solo autoclave."""
    ensure_tables(conn)
    carpeta = autoclave.resolve_folder(root)
    resultado = SteriflowIngestResult(
        autoclave=autoclave, folder=carpeta, folder_missing=not carpeta.is_dir()
    )
    if resultado.folder_missing:
        return resultado

    conocidos = known_start_times(conn, autoclave.code)
    for ruta in discover_reports(carpeta, pattern):
        _ingest_one(conn, autoclave, ruta, conocidos, resultado, force=force)
    return resultado


def _ingest_one(
    conn: sqlite3.Connection,
    autoclave: SteriflowAutoclave,
    ruta: Path,
    conocidos: set,
    resultado: SteriflowIngestResult,
    *,
    force: bool,
) -> None:
    try:
        if not force and _ya_importado(conn, autoclave.code, ruta, conocidos):
            resultado.skipped += 1
            return
        ciclo = read_report(ruta)
    except SteriflowReadError as exc:
        resultado.errors.append(str(exc))
        return
    except Exception as exc:  # PDF corrupto, permisos, fichero en uso...
        resultado.errors.append(f"{ruta.name}: {exc}")
        return

    if ciclo.autoclave_code != autoclave.code:
        # El PDF dice pertenecer a otra maquina. Guardarlo bajo este autoclave
        # falsearia el historico en silencio.
        resultado.errors.append(
            f"{ruta.name}: el informe es del autoclave {ciclo.autoclave_code}, "
            f"no del {autoclave.code}"
        )
        return

    # Un ciclo por transaccion: un PDF ilegible a mitad de carpeta no debe tirar
    # abajo los que ya se habian leido bien, ni cancelar a mitad perder lo hecho.
    conn.execute("BEGIN")
    try:
        _, era_nuevo = save_cycle(conn, ciclo)
    except Exception:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")

    conocidos.add(ciclo.started_at)
    if era_nuevo:
        resultado.cycles_new += 1
    else:
        resultado.cycles_updated += 1


def _ya_importado(
    conn: sqlite3.Connection, code: int, ruta: Path, conocidos: set
) -> bool:
    """Si este informe ya esta guardado, a ser posible sin tocar el fichero.

    Dos caminos, y el orden importa:

      1. Por el instante que lleva el NOMBRE ('[01_06_2026_01_01_20]'), que es
         el mismo que la cabecera del PDF. Cuesta cero: ni se abre el fichero.
      2. Si el nombre no lo lleva -renombrado a mano-, por sha256 del
         contenido. Hashear cuesta ~1 ms, nada al lado de abrir el PDF.

    Lo caro es siempre abrir el PDF (~320 ms), asi que lo que hay que evitar a
    toda costa es llegar a `read_report` con un informe ya conocido.
    """
    inicio = started_at_from_filename(ruta)
    if inicio is not None:
        return inicio in conocidos
    return find_by_sha(conn, code, sha256_of(ruta)) is not None
