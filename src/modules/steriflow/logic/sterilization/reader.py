"""Lectura del dato de esterilización de un informe PDF de Steriflow.

Cada PDF trae en la tabla HISTORIAL MEDIDAS una fila por fase:

    Fase Type        Inicio:  Fin:     Time phase length  T fin  T media  Min.   Max.
    3    Calentam.   01:18:08 01:30:15 00:12:07           128.94 128.66   124.44 129.53

De todas ellas solo se guarda la de esterilización -la meseta-, pero **no es
siempre la 3**: el número de fases cambia con el programa (se han visto
informes de 4, 6, 7 y 8) y con él la posición de la meseta. En 'TOMATE PELADO
1KG' es la 2 y la 3 ya es un enfriamiento; en 'TOMATE PELADO 1l2KG' es la 4.
Leerla por número fijo guardaba, en esos programas, la temperatura de un
enfriamiento como si fuera la esterilización.

Se elige por la estructura del ciclo, que es la misma en todos: primero las
fases de calentamiento y al final las de enfriamiento (`Enfriamiento N`,
`Forced cool. N`). La esterilización es **la última fase antes de que empiece a
enfriar**; ahí es donde la máquina mantiene la meseta.

Se lee esta tabla y no la sección LISTA DE DATOS -que trae la serie muestra a
muestra- por dos razones: es la única que hace falta, y además es más exacta.
El min/max de HISTORIAL MEDIDAS sale del muestreo interno de la máquina; LISTA
DE DATOS imprime una muestra cada 30 s y en la fase de esterilización del
informe de ejemplo deja fuera el mínimo real (124,84 impreso frente a 124,44
medido).

Las horas de la tabla son hora del día sin fecha; la fecha sale del corchete
de la cabecera ('[01/06/2026 01:01:20]').

Un dato que no se puede leer bien nunca tira el ciclo entero: la cabecera (que
identifica el ciclo) se guarda si se pudo leer, y cualquier problema en la fila
de la esterilización -columnas pegadas, hora ilegible, tabla que no aparece-
deja los campos afectados a None y marca `needs_review` con el motivo, en vez
de perder el ciclo o el dato en silencio.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from src.modules.steriflow.logic.sterilization.hashing import sha256_of
from src.modules.steriflow.logic.sterilization.models import SterilizationCycle

_SECCION = "HISTORIAL MEDIDAS"

# Tipos de fase que son enfriamiento. Sobre 220 informes de las seis carpetas
# solo aparecen tres tipos -"Calentam.", "Enfriamiento 1" y "Forced cool. 1"-,
# así que basta con reconocer los de enfriar: todo lo demás es calentar o
# mantener. Se incluyen las raíces en inglés y francés porque el informe las
# mezcla ya hoy ("Forced cool.") y el idioma lo fija la máquina, no la app.
_RE_ENFRIAMIENTO = re.compile(r"enfri|cool|refroid", re.IGNORECASE)

# Pie de página: la máquina numera cada sección por separado ('1/1' en
# HISTORIAL MEDIDAS). Permite saber que la tabla ya está completa sin abrir la
# página siguiente para comprobarlo.
_RE_PIE = re.compile(r"(\d+)\s*/\s*(\d+)\s*$")

_RE_INICIO_CICLO = re.compile(r"\[(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\]")
_RE_AUTOCLAVE = re.compile(r"C[oó]d\.\s*Autoclave\s*:?\s*(\d+)")
_RE_NUM_CICLO = re.compile(r"N[uú]mero\s+de\s+ciclo\s*:?\s*(\S+)")
_RE_CONCEPTO = re.compile(r"^Concep\.\s*:?\s*(.+?)\s*$", re.MULTILINE)
_RE_CONTADOR = re.compile(r"Cycles\s+Counter\s+(\d+)")
_RE_FECHA_INFORME = re.compile(
    r"^Fecha\s*:?\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})", re.MULTILINE
)

# Fila de fase completa: número, tipo, tres horas y cuatro temperaturas. El
# tipo se captura de forma no ávida porque tiene número de palabras variable
# ("Calentam.", "Enfriamiento 1", "Forced cool. 1"): lo que delimita el campo
# es la primera hora, no un número fijo de palabras.
_RE_FILA_FASE_COMPLETA = re.compile(
    r"^(\d+)\s+(\S.*?)\s+"
    r"(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+"
    r"(-?\d+[.,]\d+)\s+(-?\d+[.,]\d+)\s+(-?\d+[.,]\d+)\s+(-?\d+[.,]\d+)\s*$"
)
# Igual, pero sin exigir que las cuatro temperaturas cuadren en columnas
# separadas: cuando pdfplumber las pega sin espacio (o falta el decimal de
# alguna), la fila entera no encajaba en `_RE_FILA_FASE_COMPLETA` y antes se
# descartaba sin más. El tipo y las tres horas siguen siendo fiables -llevan
# ':' y no se pegan entre sí-, así que se localizan aquí igual y el resto de
# la fila se intenta separar aparte (ver `_completar_fase`).
_RE_FILA_FASE_PARCIAL = re.compile(
    r"^(\d+)\s+(\S.*?)\s+"
    r"(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+(.*)$"
)
# El formato de informe siempre imprime dos decimales ("128.94", "124.44"...).
# Capar aquí a exactamente dos es lo que permite separar temperaturas pegadas
# sin espacio ("128.94128.66" -> "128.94" + "128.66"): con `\d+` sin capar, el
# primer número se come de más los dígitos del segundo.
_RE_NUMERO_SUELTO = re.compile(r"-?\d+[.,]\d{2}")

# Tolerancia entre la duración impresa ("Time phase length") y la calculada a
# partir de inicio/fin ya resueltos con fecha: una discrepancia mayor delata
# que la resolución de medianoche adivinó mal el cruce de día.
_DURACION_TOLERANCIA_S = 60


class SteriflowReadError(ValueError):
    """El PDF no tiene la forma de un informe de ciclo de Steriflow."""


@dataclass(slots=True)
class _FilaFase:
    """Una fila de HISTORIAL MEDIDAS, ya separada en campos pero sin
    interpretar: las horas siguen siendo texto (no llevan fecha hasta que se
    resuelven contra el arranque del ciclo) y las temperaturas también (pueden
    venir pegadas y hay que decidir qué hacer con ellas)."""

    numero: int
    tipo: str
    inicio: str
    fin: str
    duracion: str
    temperaturas: list[str]
    # La línea tal cual, para poder citarla en una nota de revisión.
    linea: str

    @property
    def es_enfriamiento(self) -> bool:
        return _RE_ENFRIAMIENTO.search(self.tipo) is not None


def _abrir_pdfplumber():
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise SteriflowReadError(
            "Falta la dependencia 'pdfplumber', necesaria para leer los informes "
            "de Steriflow. Instalala con: pip install pdfplumber"
        ) from exc
    return pdfplumber


def _hora_segura(texto: str) -> dt.time | None:
    try:
        h, m, s = (int(p) for p in texto.split(":"))
        return dt.time(h, m, s)
    except ValueError:
        return None


def _segundos_seguro(texto: str) -> int | None:
    try:
        h, m, s = (int(p) for p in texto.split(":"))
        return h * 3600 + m * 60 + s
    except ValueError:
        return None


def _numero(texto: str) -> float | None:
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def _seccion_completa(texto: str) -> bool:
    """True si esta página trae la tabla y la sección no continúa en la siguiente."""
    if _SECCION not in texto:
        return False
    lineas = [ln for ln in texto.splitlines() if ln.strip()]
    if not lineas:
        return False
    m = _RE_PIE.search(lineas[-1])
    # Sin pie legible se sigue leyendo: mejor tardar de más que cortar la tabla.
    return m is not None and m.group(1) == m.group(2)


def read_report(path: Path | str) -> SterilizationCycle:
    """Lee un informe PDF y devuelve su dato de esterilización.

    Se deja de leer en cuanto HISTORIAL MEDIDAS está completa, en vez de
    extraer también la gráfica y LISTA DE DATOS -las páginas más caras del
    informe y las únicas que no hacen falta-.
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
    _leer_fase_esterilizacion(paginas, ciclo)
    return ciclo


def _leer_cabecera(texto: str, path: Path) -> SterilizationCycle:
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

    # El lote es la línea de cabecera entera, tal cual: es lo que identifica el
    # ciclo en la máquina. Si ninguna línea trae el corchete de inicio -el
    # informe wrappeó la cabecera de otra forma-, se deja en blanco: es un
    # campo informativo, no crítico, y no hace falta marcar el ciclo por esto.
    lote = ""
    for linea in texto.splitlines():
        if m_inicio.group(0) in linea:
            lote = re.sub(r"^N[uú]mero\s+lote\s*", "", linea).strip()
            lote = re.sub(r"\s+Steriflow$", "", lote).strip()
            break

    return SterilizationCycle(
        # Los dos salen del PDF: quien conoce el número real de la máquina es
        # la configuración, y es `sterilization/service.py` -que sabe de qué
        # autoclave se está extrayendo- quien corrige `autoclave_code`.
        autoclave_code=int(m_autoclave.group(1)),
        reported_code=int(m_autoclave.group(1)),
        started_at=started_at,
        source_filename=path.name,
        source_sha256=sha256_of(path),
        batch=lote,
        cycle_number=m_ciclo.group(1) if m_ciclo else "",
        product=m_concepto.group(1).strip() if m_concepto else "",
        reported_at=reported_at,
        cycles_counter=int(m_contador.group(1)) if m_contador else None,
    )


def _leer_fase_esterilizacion(paginas: list[str], ciclo: SterilizationCycle) -> None:
    pagina = next((p for p in paginas if _SECCION in p), None)
    if pagina is None:
        ciclo.needs_review = True
        _anadir_nota(ciclo, f"El informe no tiene sección '{_SECCION}'")
        return

    # Solo desde el título de la sección hacia abajo: ahora que la fase se
    # elige por su posición entre las demás, una fila con esta misma forma
    # impresa más arriba en la página correría la cuenta y haría elegir otra.
    filas = _leer_filas_de_fase(pagina[pagina.index(_SECCION):])
    if not filas:
        # Un ciclo abortado nada más arrancar imprime la tabla con guiones
        # ("- - - - - - - - -") y ninguna fila de fase.
        ciclo.needs_review = True
        _anadir_nota(ciclo, f"No hay ninguna fila de fase en {_SECCION}")
        return

    fase = _elegir_fase_esterilizacion(filas, ciclo)
    if fase is None:
        return

    ciclo.sterilization_phase_number = fase.numero
    ciclo.sterilization_phase_type = fase.tipo

    temperaturas: list[str | None] = list(fase.temperaturas)
    if len(temperaturas) != 4:
        # No se sabe CUÁL de las cuatro falta o sobra, así que no se asignan
        # por posición -eso guardaría un valor en la columna equivocada sin
        # que nada lo delate-: las cuatro quedan a None y se marca para
        # revisión.
        ciclo.needs_review = True
        _anadir_nota(
            ciclo,
            f"Fase {fase.numero}: se esperaban 4 temperaturas y se leyeron "
            f"{len(temperaturas)}: '{fase.linea}'",
        )
        temperaturas = [None, None, None, None]

    _completar_fase(ciclo, fase, temperaturas)


def _leer_filas_de_fase(pagina: str) -> list[_FilaFase]:
    """Todas las filas de fase de la tabla, en el orden impreso.

    Cada línea se prueba primero contra el patrón completo y, si no encaja,
    contra el parcial: así una fila con las temperaturas pegadas (que el
    patrón completo rechaza) sigue aportando su tipo y sus tres horas, en vez
    de desaparecer de la lista y descolocar la elección de la fase.
    """
    filas: list[_FilaFase] = []
    for linea in pagina.splitlines():
        linea = linea.strip()

        m = _RE_FILA_FASE_COMPLETA.match(linea)
        if m is not None:
            numero, tipo, inicio, fin, duracion, *temperaturas = m.groups()
            filas.append(_FilaFase(int(numero), tipo.strip(), inicio, fin, duracion,
                                   list(temperaturas), linea))
            continue

        m = _RE_FILA_FASE_PARCIAL.match(linea)
        if m is not None:
            numero, tipo, inicio, fin, duracion, resto = m.groups()
            filas.append(_FilaFase(int(numero), tipo.strip(), inicio, fin, duracion,
                                   _RE_NUMERO_SUELTO.findall(resto), linea))

    return filas


def _elegir_fase_esterilizacion(
    filas: list[_FilaFase], ciclo: SterilizationCycle
) -> _FilaFase | None:
    """La última fase antes del primer enfriamiento (ver el docstring del módulo).

    Devuelve None -y deja el ciclo marcado- cuando el informe no permite
    decidir: si la primera fase ya es de enfriamiento no hay ninguna meseta
    que guardar, y quedarse con la anterior sería inventarse el dato.
    """
    primer_enfriamiento = next(
        (i for i, fila in enumerate(filas) if fila.es_enfriamiento), None
    )

    if primer_enfriamiento is None:
        # El ciclo se cortó antes de enfriar (o la máquina imprimió tipos que
        # no reconocemos). La última fase es lo más parecido a la meseta, pero
        # no hay forma de confirmarlo desde el informe: se guarda y se avisa.
        ciclo.needs_review = True
        _anadir_nota(
            ciclo,
            "El informe no llega a enfriar: se toma la última fase "
            f"({filas[-1].numero} {filas[-1].tipo}) como esterilización",
        )
        return filas[-1]

    if primer_enfriamiento == 0:
        ciclo.needs_review = True
        _anadir_nota(
            ciclo,
            f"La primera fase del informe ya es de enfriamiento "
            f"({filas[0].tipo}): no hay fase de esterilización que leer",
        )
        return None

    return filas[primer_enfriamiento - 1]


def _completar_fase(
    ciclo: SterilizationCycle,
    fase: _FilaFase,
    temperaturas: list[str | None],
) -> None:
    hora_inicio = _hora_segura(fase.inicio)
    hora_fin = _hora_segura(fase.fin)
    duracion_impresa = _segundos_seguro(fase.duracion)

    if hora_inicio is None or hora_fin is None:
        ciclo.needs_review = True
        _anadir_nota(ciclo, f"Fase {fase.numero}: hora de inicio o fin ilegible")
    else:
        inicio_dt, fin_dt = _resolver_fechas_fase(ciclo.started_at, hora_inicio, hora_fin)
        ciclo.sterilization_start_ts = inicio_dt
        ciclo.sterilization_end_ts = fin_dt

        duracion_calculada = int((fin_dt - inicio_dt).total_seconds())
        ciclo.sterilization_duration_s = (
            duracion_impresa if duracion_impresa is not None else duracion_calculada
        )
        if (
            duracion_impresa is not None
            and abs(duracion_calculada - duracion_impresa) > _DURACION_TOLERANCIA_S
        ):
            ciclo.needs_review = True
            _anadir_nota(
                ciclo,
                f"Fase {fase.numero}: la duración calculada ({duracion_calculada}s) no "
                f"coincide con la impresa ({duracion_impresa}s)",
            )

    valores: list[float | None] = []
    conversion_fallida = False
    for token in temperaturas:
        if token is None:
            valores.append(None)
            continue
        valor = _numero(token)
        valores.append(valor)
        if valor is None:
            conversion_fallida = True

    (
        ciclo.sterilization_temp_end_c,
        ciclo.sterilization_temp_mean_c,
        ciclo.sterilization_temp_min_c,
        ciclo.sterilization_temp_max_c,
    ) = valores

    if conversion_fallida:
        ciclo.needs_review = True
        _anadir_nota(
            ciclo,
            f"Fase {fase.numero}: alguna temperatura no se pudo interpretar como número",
        )


def _resolver_fechas_fase(
    started_at: dt.datetime, hora_inicio: dt.time, hora_fin: dt.time
) -> tuple[dt.datetime, dt.datetime]:
    """Resuelve la fecha de la fase a partir de la hora de arranque del ciclo.

    Las horas de la tabla no llevan fecha. Si la hora de inicio de la fase es
    anterior a la de arranque del ciclo, el ciclo cruzó la medianoche antes de
    llegar a ella; lo mismo si la de fin es anterior a la de inicio de la
    propia fase. Al necesitar solo esta fase no hace falta recorrer las
    anteriores en orden para llegar a la misma conclusión.
    """
    fecha_inicio = started_at.date()
    if hora_inicio < started_at.time():
        fecha_inicio += dt.timedelta(days=1)
    inicio_dt = dt.datetime.combine(fecha_inicio, hora_inicio)

    fecha_fin = fecha_inicio
    if hora_fin < hora_inicio:
        fecha_fin += dt.timedelta(days=1)
    fin_dt = dt.datetime.combine(fecha_fin, hora_fin)

    return inicio_dt, fin_dt


def _anadir_nota(ciclo: SterilizationCycle, nota: str) -> None:
    ciclo.review_notes = f"{ciclo.review_notes}; {nota}" if ciclo.review_notes else nota
