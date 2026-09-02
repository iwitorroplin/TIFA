"""Lectura de un informe PDF de Steriflow.

Cada PDF es un ciclo completo y trae cuatro secciones. La que se lee aqui es
HISTORIAL MEDIDAS, la tabla resumen fase a fase:

    Fase Type        Inicio:  Fin:     Time phase length  T fin  T media  Min.   Max.
    3    Calentam.   01:18:08 01:30:15 00:12:07           128.94 128.66   124.44 129.53

Se lee ESA tabla y no la seccion LISTA DE DATOS -que trae la serie muestra a
muestra- por dos razones: es lo unico que el sistema muestra por ahora, y ademas
es mas exacta. El min/max de HISTORIAL MEDIDAS sale del muestreo interno de la
maquina; LISTA DE DATOS imprime una muestra cada 30 s y en la fase 3 del informe
de ejemplo se deja fuera el minimo real (124,84 impreso frente a 124,44 medido).

Las horas de la tabla son hora del dia sin fecha. La fecha sale del corchete de
la cabecera ('[01/06/2026 01:01:20]') y las fases se resuelven en orden
creciente: un ciclo que empieza a las 23:40 y acaba a las 00:50 cruza la
medianoche, y sin esa correccion sus duraciones salen negativas.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from ..io.base import sha256_of  # utilidad de hash, sin relacion con el lector de Ferlo
from .models import SteriflowCycle, SteriflowPhase

# Titulo de la seccion cuya tabla se lee.
_SECCION = "HISTORIAL MEDIDAS"

# Pie de pagina: la maquina numera cada seccion por separado ('1/1' en
# HISTORIAL MEDIDAS, '1/3'..'3/3' en LISTA DE DATOS). Es lo que permite saber
# que la tabla ya esta completa sin abrir la pagina siguiente para comprobarlo.
_RE_PIE = re.compile(r"(\d+)\s*/\s*(\d+)\s*$")

# Identidad del ciclo en el nombre del fichero:
#   MPI_6_003_-_GUISANTE_1¡2_[01_06_2026_01_01_20].pdf
# El corchete es el mismo instante de arranque que la cabecera del PDF, asi que
# sirve para saber si un informe ya esta importado SIN abrirlo. Ver
# `service.ingest_autoclave`.
_RE_NOMBRE = re.compile(
    r"\[(\d{2})_(\d{2})_(\d{4})_(\d{2})_(\d{2})_(\d{2})\]"
)

_RE_INICIO_CICLO = re.compile(r"\[(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\]")
_RE_AUTOCLAVE = re.compile(r"C[oó]d\.\s*Autoclave\s*:?\s*(\d+)")
_RE_NUM_CICLO = re.compile(r"N[uú]mero\s+de\s+ciclo\s*:?\s*(\S+)")
_RE_CONCEPTO = re.compile(r"^Concep\.\s*:?\s*(.+?)\s*$", re.MULTILINE)
_RE_CONTADOR = re.compile(r"Cycles\s+Counter\s+(\d+)")
_RE_FECHA_INFORME = re.compile(
    r"^Fecha\s*:?\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})", re.MULTILINE
)

# Fase | tipo | inicio | fin | duracion | T fin | T media | T min | T max.
# El tipo se captura de forma no avida porque tiene numero de palabras variable
# ("Calentam.", "Enfriamiento 1", "Forced cool. 1"): lo que delimita el campo es
# la primera hora, no un numero fijo de palabras.
_RE_FILA_FASE = re.compile(
    r"^(\d+)\s+(\S.*?)\s+"
    r"(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+"
    r"(-?\d+[.,]\d+)\s+(-?\d+[.,]\d+)\s+(-?\d+[.,]\d+)\s+(-?\d+[.,]\d+)\s*$"
)


class SteriflowReadError(ValueError):
    """El PDF no tiene la forma de un informe de ciclo de Steriflow."""


def _abrir_pdfplumber():
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise SteriflowReadError(
            "Falta la dependencia 'pdfplumber', necesaria para leer los informes "
            "de Steriflow. Instalala con: pip install pdfplumber"
        ) from exc
    return pdfplumber


def _hora(texto: str) -> dt.time:
    h, m, s = (int(p) for p in texto.split(":"))
    return dt.time(h, m, s)


def _segundos(texto: str) -> int:
    h, m, s = (int(p) for p in texto.split(":"))
    return h * 3600 + m * 60 + s


def _numero(texto: str) -> float | None:
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def started_at_from_filename(path: Path | str) -> dt.datetime | None:
    """Instante de arranque segun el NOMBRE del fichero, sin abrirlo.

    Devuelve None si el nombre no lleva el corchete -un informe renombrado a
    mano, por ejemplo-, y entonces toca abrirlo para saber de que ciclo es.
    """
    m = _RE_NOMBRE.search(Path(path).name)
    if m is None:
        return None
    dia, mes, anio, hh, mm, ss = (int(g) for g in m.groups())
    try:
        return dt.datetime(anio, mes, dia, hh, mm, ss)
    except ValueError:
        return None


def _seccion_completa(texto: str) -> bool:
    """True si esta pagina trae la tabla y la seccion no continua en la siguiente."""
    if _SECCION not in texto:
        return False
    lineas = [ln for ln in texto.splitlines() if ln.strip()]
    if not lineas:
        return False
    m = _RE_PIE.search(lineas[-1])
    # Sin pie legible se sigue leyendo: mejor tardar de mas que cortar la tabla.
    return m is not None and m.group(1) == m.group(2)


def read_report(path: Path | str) -> SteriflowCycle:
    """Lee un informe PDF y devuelve el ciclo con sus fases.

    Se deja de leer en cuanto HISTORIAL MEDIDAS esta completa. No es una
    micro-optimizacion: extraer el texto de las nueve paginas del informe de
    referencia cuesta 1.150 ms y pararse al acabar esa seccion, 340 ms. Las
    paginas que se ahorran son la grafica y LISTA DE DATOS -la serie muestra a
    muestra-, que son las mas caras y las unicas que no se usan. Sobre una
    carpeta de 2.000 informes son 38 minutos frente a 11.
    """
    path = Path(path)
    pdfplumber = _abrir_pdfplumber()

    paginas: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text() or ""
            paginas.append(texto_pagina)
            if _seccion_completa(texto_pagina):
                break

    texto = "\n".join(paginas)
    if not texto.strip():
        raise SteriflowReadError(
            f"{path.name}: el PDF no tiene texto extraible (¿es un escaneo?)"
        )

    ciclo = _leer_cabecera(texto, path)
    ciclo.phases = _leer_fases(paginas, path, ciclo.started_at)
    return ciclo


def _leer_cabecera(texto: str, path: Path) -> SteriflowCycle:
    m_inicio = _RE_INICIO_CICLO.search(texto)
    if m_inicio is None:
        raise SteriflowReadError(
            f"{path.name}: no se encuentra la fecha de inicio de ciclo en la "
            f"cabecera (se espera un corchete tipo '[01/06/2026 01:01:20]')"
        )
    dia, mes, anio, hh, mm, ss = (int(g) for g in m_inicio.groups())
    started_at = dt.datetime(anio, mes, dia, hh, mm, ss)

    m_autoclave = _RE_AUTOCLAVE.search(texto)
    if m_autoclave is None:
        raise SteriflowReadError(
            f"{path.name}: no se encuentra 'Cod. Autoclave' en la cabecera"
        )

    reported_at = None
    m_fecha = _RE_FECHA_INFORME.search(texto)
    if m_fecha is not None:
        d, mo, y, h, mi, s = (int(g) for g in m_fecha.groups())
        reported_at = dt.datetime(y, mo, d, h, mi, s)

    m_contador = _RE_CONTADOR.search(texto)
    m_ciclo = _RE_NUM_CICLO.search(texto)
    m_concepto = _RE_CONCEPTO.search(texto)

    # El lote es la linea de cabecera entera, tal cual: es lo que identifica el
    # ciclo en la maquina y en el nombre del fichero.
    lote = ""
    for linea in texto.splitlines():
        if m_inicio.group(0) in linea:
            lote = re.sub(r"^N[uú]mero\s+lote\s*", "", linea).strip()
            lote = re.sub(r"\s+Steriflow$", "", lote).strip()
            break

    return SteriflowCycle(
        autoclave_code=int(m_autoclave.group(1)),
        started_at=started_at,
        source_filename=path.name,
        source_sha256=sha256_of(path),
        batch=lote,
        cycle_number=m_ciclo.group(1) if m_ciclo else "",
        product=m_concepto.group(1).strip() if m_concepto else "",
        reported_at=reported_at,
        cycles_counter=int(m_contador.group(1)) if m_contador else None,
    )


def _leer_fases(
    paginas: list[str], path: Path, started_at: dt.datetime
) -> list[SteriflowPhase]:
    pagina = next((p for p in paginas if _SECCION in p), None)
    if pagina is None:
        raise SteriflowReadError(
            f"{path.name}: el informe no tiene seccion '{_SECCION}'"
        )

    crudas: list[tuple] = []
    for linea in pagina.splitlines():
        m = _RE_FILA_FASE.match(linea.strip())
        if m is not None:
            crudas.append(m.groups())
    if not crudas:
        raise SteriflowReadError(
            f"{path.name}: la seccion '{_SECCION}' no tiene ninguna fila de fase legible"
        )

    # Las horas de la tabla no llevan fecha. Se recorren en orden creciente
    # partiendo del arranque del ciclo: cada vez que una hora es anterior a la
    # anterior, el ciclo ha cruzado la medianoche y toca sumar un dia.
    fecha = started_at.date()
    previa = started_at.time()

    def resolver(texto: str) -> dt.datetime:
        nonlocal fecha, previa
        hora = _hora(texto)
        if hora < previa:
            fecha += dt.timedelta(days=1)
        previa = hora
        return dt.datetime.combine(fecha, hora)

    fases: list[SteriflowPhase] = []
    for numero, tipo, inicio, fin, duracion, t_fin, t_media, t_min, t_max in crudas:
        fases.append(SteriflowPhase(
            number=int(numero),
            type_name=tipo.strip(),
            start_ts=resolver(inicio),
            end_ts=resolver(fin),
            duration_s=_segundos(duracion),
            temperature_end_c=_numero(t_fin),
            temperature_mean_c=_numero(t_media),
            temperature_min_c=_numero(t_min),
            temperature_max_c=_numero(t_max),
        ))
    return fases
